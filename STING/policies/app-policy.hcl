# Allow tokens to look up their own properties
path "auth/token/lookup-self" {
    capabilities = ["read"]
}

# Allow tokens to renew themselves
path "auth/token/renew-self" {
    capabilities = ["update"]
}

# Allow tokens to revoke themselves
path "auth/token/revoke-self" {
    capabilities = ["update"]
}

# Allow read access to KV v2 secrets in the sting/ path
path "sting/*" {
    capabilities = ["read"]
}

# Allow read access to database credentials
path "sting/database/*" {
    capabilities = ["read"]
}

# Allow read access to Keycloak credentials
path "sting/keycloak/*" {
    capabilities = ["read"]
}
