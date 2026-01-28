from flask import Blueprint, jsonify, request, current_app
import logging
import os
from ..utils.decorators import development_only
import psycopg2
from psycopg2.extras import RealDictCursor
import subprocess
import json
from functools import wraps
import time

debug_blueprint = Blueprint('debug', __name__)
logger = logging.getLogger(__name__)

@debug_blueprint.route('/api/debug/verification-flows', methods=['GET'])
@development_only
def get_verification_flows():
    """
    Get active verification flows for debugging
    DEVELOPMENT USE ONLY - This endpoint should never be enabled in production
    """
    try:
        # Get database connection from environment variables
        db_host = os.environ.get('POSTGRES_HOST', 'db')
        db_port = os.environ.get('POSTGRES_PORT', '5432')
        db_name = os.environ.get('POSTGRES_DB', 'sting_app')
        db_user = os.environ.get('POSTGRES_USER', 'postgres')
        db_password = os.environ.get('POSTGRES_PASSWORD', 'postgres')
        
        # Connect to the database
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            dbname=db_name,
            user=db_user,
            password=db_password
        )
        
        # Create a cursor that returns dictionaries
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Query to get verification flows with email addresses
        query = """
        SELECT 
            f.id, 
            f.state, 
            f.created_at, 
            f.expires_at,
            a.value as email,
            t.token
        FROM 
            selfservice_verification_flows f
        LEFT JOIN 
            identity_verifiable_addresses a ON f.id = a.via
        LEFT JOIN
            identity_verification_tokens t ON t.identity_verifiable_address_id = a.id
        WHERE 
            f.state = 'sent_email'
        ORDER BY 
            f.created_at DESC
        LIMIT 10
        """
        
        cursor.execute(query)
        flows = cursor.fetchall()
        
        # Convert flows to a list of dictionaries and add verification URLs
        result = []
        for flow in flows:
            flow_dict = dict(flow)
            # Add verification URL if token exists
            if flow_dict.get('token'):
                flow_dict['verification_url'] = (
                    f"{current_app.config.get('KRATOS_PUBLIC_URL')}"
                    f"/self-service/verification?flow={flow_dict['id']}&token={flow_dict['token']}"
                )
            result.append(flow_dict)
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'flows': result
        })
    
    except Exception as e:
        logger.error(f"Error fetching verification flows: {e}")
        return jsonify({
            'success': False,
            'message': f"Error fetching verification flows: {str(e)}"
        }), 500

@debug_blueprint.route('/api/debug/bypass-verification', methods=['POST'])
@development_only
def bypass_verification():
    """
    Bypass email verification for a user
    DEVELOPMENT USE ONLY - This endpoint should never be enabled in production
    """
    try:
        data = request.json
        email = data.get('email')
        
        if not email:
            return jsonify({
                'success': False,
                'message': 'Email is required'
            }), 400
        
        # Get database connection from environment variables
        db_host = os.environ.get('POSTGRES_HOST', 'db')
        db_port = os.environ.get('POSTGRES_PORT', '5432')
        db_name = os.environ.get('POSTGRES_DB', 'sting_app')
        db_user = os.environ.get('POSTGRES_USER', 'postgres')
        db_password = os.environ.get('POSTGRES_PASSWORD', 'postgres')
        
        # Connect to the database
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            dbname=db_name,
            user=db_user,
            password=db_password
        )
        
        # Create a cursor
        cursor = conn.cursor()
        
        # Update the verified status of the email address
        query = """
        UPDATE identity_verifiable_addresses
        SET verified = TRUE
        WHERE value = %s
        RETURNING id
        """
        
        cursor.execute(query, (email,))
        result = cursor.fetchone()
        
        if not result:
            return jsonify({
                'success': False,
                'message': f'Email address {email} not found'
            }), 404
        
        # Commit the transaction
        conn.commit()
        
        # Close cursor and connection
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Verification bypassed for {email}'
        })
    
    except Exception as e:
        logger.error(f"Error bypassing verification: {e}")
        return jsonify({
            'success': False,
            'message': f"Error bypassing verification: {str(e)}"
        }), 500

def require_dev_mode(f):
    """Decorator to ensure debug endpoints only work in development mode"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if we're in development mode
        if current_app.config.get('FLASK_ENV') != 'development' and not current_app.debug:
            return jsonify({'error': 'Debug endpoints only available in development mode'}), 403
        return f(*args, **kwargs)
    return decorated_function

@debug_blueprint.route('/api/debug/clear-users', methods=['POST'])
@development_only
@require_dev_mode
def clear_users():
    """Clear all user data for development purposes"""
    try:
        logger.info("Starting user data clearing process...")
        
        # Import database and models
        from app.database import db
        import requests
        
        results = []
        errors = []
        
        # 1. Clear Kratos identities via Admin API
        try:
            kratos_admin_url = os.environ.get('KRATOS_ADMIN_URL', 'http://kratos:4434')
            
            # Get all identities
            response = requests.get(f"{kratos_admin_url}/admin/identities", timeout=10)
            if response.status_code == 200:
                identities = response.json()
                deleted_count = 0
                
                for identity in identities:
                    identity_id = identity.get('id')
                    if identity_id:
                        delete_response = requests.delete(
                            f"{kratos_admin_url}/admin/identities/{identity_id}",
                            timeout=10
                        )
                        if delete_response.status_code in [200, 204, 404]:
                            deleted_count += 1
                
                results.append(f"Deleted {deleted_count} Kratos identities")
            elif response.status_code == 400:
                # Likely no identities exist
                results.append("No Kratos identities found to delete")
            else:
                errors.append(f"Failed to fetch Kratos identities: {response.status_code}")
                
        except Exception as e:
            errors.append(f"Kratos cleanup error: {str(e)}")
        
        # 2. Clear application database tables
        try:
            with current_app.app_context():
                # Clear user-related tables (order matters for foreign keys)
                tables_to_clear = [
                    'user_sessions',
                    'app_sessions', 
                    'audit_logs',
                    'users',
                    'app_users'
                ]
                
                cleared_tables = []
                for table_name in tables_to_clear:
                    try:
                        # Use a separate transaction for each table
                        result = db.session.execute(db.text(f"DELETE FROM {table_name}"))
                        db.session.commit()
                        cleared_tables.append(f"{table_name} ({result.rowcount} rows)")
                    except Exception as table_error:
                        # Rollback this transaction and continue
                        db.session.rollback()
                        if "does not exist" not in str(table_error):
                            errors.append(f"Table {table_name}: {str(table_error)}")
                
                # Reset sequences
                try:
                    db.session.execute(db.text("ALTER SEQUENCE users_id_seq RESTART WITH 1"))
                    db.session.commit()
                except Exception:
                    db.session.rollback()  # Sequence might not exist
                results.append(f"Cleared database tables: {', '.join(cleared_tables)}")
                
        except Exception as e:
            errors.append(f"Database cleanup error: {str(e)}")
            try:
                db.session.rollback()
            except:
                pass
        
        # 3. Clear Kratos sessions
        try:
            kratos_admin_url = os.environ.get('KRATOS_ADMIN_URL', 'http://kratos:4434')
            response = requests.delete(f"{kratos_admin_url}/admin/sessions", timeout=10)
            if response.status_code in [200, 204]:
                results.append("Cleared Kratos sessions")
            else:
                errors.append(f"Failed to clear Kratos sessions: {response.status_code}")
        except Exception as e:
            errors.append(f"Kratos session cleanup error: {str(e)}")
        
        # Prepare response
        success = len(errors) == 0
        message = "User data cleared successfully" if success else "User data partially cleared with some errors"
        
        response_data = {
            'success': success,
            'message': message,
            'results': results,
            'errors': errors if errors else None
        }
        
        logger.info(f"User data clearing completed. Success: {success}")
        return jsonify(response_data)
            
    except Exception as e:
        logger.error(f"Error clearing user data: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to clear user data: {str(e)}'
        }), 500

@debug_blueprint.route('/api/debug/fix-msting', methods=['POST'])
@development_only
@require_dev_mode
def fix_msting():
    """Fix/install the msting command"""
    try:
        # Get the script directory
        script_dir = os.path.join(os.path.dirname(__file__), '..', '..')
        script_path = os.path.join(script_dir, 'fix_msting_installation.sh')
        
        if not os.path.exists(script_path):
            return jsonify({
                'success': False,
                'error': 'Fix msting script not found',
                'path': script_path
            }), 404
        
        logger.info("Starting msting command fix process...")
        
        # Run the script
        env = os.environ.copy()
        
        process = subprocess.Popen(
            ['bash', script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=script_dir,
            env=env
        )
        
        # Get output with timeout
        try:
            stdout, stderr = process.communicate(timeout=60)  # 1 minute timeout
            return_code = process.returncode
        except subprocess.TimeoutExpired:
            process.kill()
            return jsonify({
                'success': False,
                'error': 'Script execution timed out after 1 minute'
            }), 500
        
        logger.info(f"Fix msting script completed with return code: {return_code}")
        
        if return_code == 0:
            return jsonify({
                'success': True,
                'message': 'msting command fixed/installed successfully',
                'output': stdout,
                'warnings': stderr if stderr else None
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Script execution failed',
                'return_code': return_code,
                'output': stdout,
                'stderr': stderr
            }), 500
            
    except Exception as e:
        logger.error(f"Error fixing msting command: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to fix msting command: {str(e)}'
        }), 500

@debug_blueprint.route('/api/debug/system-status', methods=['GET'])
@development_only
def system_status():
    """Get system status information"""
    try:
        script_dir = os.path.join(os.path.dirname(__file__), '..', '..')
        
        # Check script availability
        clear_script = os.path.join(script_dir, 'clear_dev_users.sh')
        msting_script = os.path.join(script_dir, 'fix_msting_installation.sh')
        
        # Check msting command availability
        msting_available = False
        try:
            result = subprocess.run(['which', 'msting'], capture_output=True, text=True)
            msting_available = result.returncode == 0
        except:
            pass
        
        # Check Docker services
        docker_services = []
        try:
            result = subprocess.run(
                ['docker-compose', 'ps', '--format', 'json'],
                capture_output=True,
                text=True,
                cwd=script_dir
            )
            if result.returncode == 0:
                # Parse each line as JSON
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        try:
                            service = json.loads(line)
                            docker_services.append({
                                'name': service.get('Service', 'unknown'),
                                'status': service.get('State', 'unknown'),
                                'health': service.get('Health', 'unknown')
                            })
                        except json.JSONDecodeError:
                            pass
        except:
            pass
        
        return jsonify({
            'success': True,
            'scripts': {
                'clear_users_available': os.path.exists(clear_script),
                'fix_msting_available': os.path.exists(msting_script),
                'clear_users_path': clear_script,
                'fix_msting_path': msting_script
            },
            'msting_command': {
                'available': msting_available,
                'location': subprocess.run(['which', 'msting'], capture_output=True, text=True).stdout.strip() if msting_available else None
            },
            'docker_services': docker_services,
            'environment': {
                'working_directory': script_dir,
                'flask_env': current_app.config.get('FLASK_ENV', 'unknown'),
                'debug_mode': current_app.debug
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting system status: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to get system status: {str(e)}'
        }), 500