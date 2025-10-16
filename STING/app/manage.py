from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from app.run import create_app, db

app = create_app()
migrate = Migrate(app, db)
manager = Manager(app)

# Add the 'db' command for database migrations
manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    manager.run()