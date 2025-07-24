#!/bin/bash

# Script to help encode secrets for Kubernetes
# Usage: ./encode-secrets.sh

echo "=== Kubernetes Secret Encoder ==="
echo "This script will help you encode your secrets for the secret.yaml file"
echo

# Function to encode and display
encode_secret() {
    local name=$1
    local prompt=$2
    local default=$3
    
    echo -n "$prompt"
    if [ ! -z "$default" ]; then
        echo -n " (default: $default)"
    fi
    echo -n ": "
    
    read -r value
    if [ -z "$value" ] && [ ! -z "$default" ]; then
        value=$default
    fi
    
    if [ ! -z "$value" ]; then
        encoded=$(echo -n "$value" | base64)
        echo "  $name: \"$encoded\""
        echo
    else
        echo "  $name: \"\"  # Empty - please update manually"
        echo
    fi
}

echo "Please enter your configuration values:"
echo "======================================="
echo

# Database configuration
echo "# Database configuration"
encode_secret "database-hostname" "Database hostname" "localhost"
encode_secret "database-port" "Database port" "5432"
encode_secret "database-password" "Database password" ""
encode_secret "database-name" "Database name" "ai_data_capture"
encode_secret "database-username" "Database username" "app_user"

echo
echo "# JWT configuration"
encode_secret "secret-key" "JWT secret key (generate a strong random key)" ""
encode_secret "algorithm" "JWT algorithm" "HS256"
encode_secret "access-token-expire-minutes" "Access token expire minutes" "30"

## AWS Secrets
echo "# AWS Screts"
encode_secret "aws-access-key" "AWS Access Key" ""
encode_secret "aws-secret-key" "AWS Secret Access Key" ""
encode_secret "aws-region" "AWS Region" "us-east-1"
encode_secret "aws-bucket-name" "AWS Bucket Name" "ai-data-capture"

# OPENAI
echo "# OpenAI"
encode_secret "openai-api-key" "OpenAI API Key" ""


echo
echo "======================================="
echo "Copy the above values to your secret.yaml file in the 'data' section"
echo "======================================="
echo

# Optional: Generate a random JWT secret key
#echo "Need a random JWT secret key? Here's one:"
#random_key=$(openssl rand -base64 32)
#encoded_key=$(echo -n "$random_key" | base64)
#echo "Random key: $random_key"
#echo "Base64 encoded: $encoded_key"
#echo
