// Add when fetching model status
if (modelStatus.unavailable_models?.llama3) {
  setWarningMessage("Premium models unavailable. Check documentation for HF_TOKEN setup.");
}
