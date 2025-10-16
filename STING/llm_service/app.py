# Add this pattern to the model initialization
available_models = {}
failed_models = {}

for model_name in config.ENABLED_MODELS:
    try:
        model_client = initialize_model_client(model_name)
        available_models[model_name] = model_client
        logger.info(f"Successfully initialized model: {model_name}")
    except Exception as e:
        failed_models[model_name] = str(e)
        logger.warning(f"Failed to initialize model {model_name}: {str(e)}")
        # Continue instead of failing

if not available_models:
    logger.error("No models were successfully initialized. Service will start but won't process requests.")
    # Still continue startup - don't exit

@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        'available_models': list(available_models.keys()),
        'unavailable_models': {
            name: reason for name, reason in failed_models.items()
        },
        'message': "Some models require Hugging Face authentication. Set HF_TOKEN environment variable to access all models." 
                   if failed_models else "All models available"
    })
