# Full access to KV v2 secrets in the sting/ path
path "sting/*" {
    capabilities = ["create", "read", "update", "delete", "list"]
}

# System health check
path "sys/health" {
    capabilities = ["read", "sudo"]
}

# Manage policies
path "sys/policies/acl/*" {
    capabilities = ["create", "read", "update", "delete", "list"]
}

# Manage token creation
path "auth/token/create" {
    capabilities = ["create", "read", "update", "list"]
}
