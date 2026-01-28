// Re-export KratosProviderRefactored as KratosProvider for backward compatibility
// This allows us to gradually migrate components without breaking existing code

export { 
  KratosProviderRefactored as KratosProvider,
  useKratos,
  KratosProviderRefactored as default
} from './KratosProviderRefactored';