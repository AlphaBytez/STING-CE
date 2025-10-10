from vault_manager import VaultManager

def main():
    vault = VaultManager()
    if vault.initialize_secrets():
        print("Vault initialized successfully")
    else:
        print("Failed to initialize Vault")

if __name__ == "__main__":
    main()