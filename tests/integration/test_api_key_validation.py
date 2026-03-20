"""
Simplified Integration Tests for BYOK API Key Validation.

Tests that the API key validation logic works correctly.
"""
import pytest
from backend.core.security import encrypt_api_key, decrypt_api_key


class TestAPIKeyValidation:
    """Test API key validation logic."""
    
    def test_valid_api_key_formats(self):
        """Test that valid API keys are accepted."""
        from backend.api.users import APIKeyUpdate
        from pydantic import ValidationError
        
        valid_keys = [
            "AIzaSyC_mock_key_for_testing_purposes_123",  # 39 chars
            "AIzaSyC_shorter_key_12345678901234567890",  # 39 chars
            "AIzaSyC-dash-key_underscore-mix-1234567890",  # With dashes/underscores
        ]
        
        for key in valid_keys:
            # Should not raise
            try:
                model = APIKeyUpdate(api_key=key)
                assert model.api_key == key
            except ValidationError as e:
                pytest.fail(f"Valid key rejected: {key}, error: {e}")
    
    def test_invalid_api_key_wrong_prefix(self):
        """Test that keys not starting with AIza are rejected."""
        from backend.api.users import APIKeyUpdate
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError) as exc_info:
            APIKeyUpdate(api_key="invalid-key-wrong-prefix-12345678901")
        
        assert "Must start with 'AIza'" in str(exc_info.value)
    
    def test_invalid_api_key_too_short(self):
        """Test that short keys are rejected."""
        from backend.api.users import APIKeyUpdate
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError) as exc_info:
            APIKeyUpdate(api_key="AIza123")  # Only 7 chars
        
        assert "Invalid API key length" in str(exc_info.value)
    
    def test_invalid_api_key_too_long(self):
        """Test that overly long keys are rejected."""
        from backend.api.users import APIKeyUpdate
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError) as exc_info:
            APIKeyUpdate(api_key="AIza" + "x" * 100)  # 104 chars
        
        assert "Invalid API key length" in str(exc_info.value)
    
    def test_invalid_api_key_special_characters(self):
        """Test that keys with invalid characters are rejected."""
        from backend.api.users import APIKeyUpdate
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError) as exc_info:
            APIKeyUpdate(api_key="AIzaSyC-test@#$%^&*()_key_12345678901")
        
        assert "invalid characters" in str(exc_info.value)
    
    def test_api_key_whitespace_stripped(self):
        """Test that whitespace is stripped from keys."""
        from backend.api.users import APIKeyUpdate
        
        key_with_whitespace = "   AIzaSyC_test_key_with_spaces_1234567890   "
        model = APIKeyUpdate(api_key=key_with_whitespace)
        
        # Should be stripped
        assert model.api_key == "AIzaSyC_test_key_with_spaces_1234567890"
        assert not model.api_key.startswith(" ")
        assert not model.api_key.endswith(" ")
    
    def test_empty_api_key_rejected(self):
        """Test that empty keys are rejected."""
        from backend.api.users import APIKeyUpdate
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError) as exc_info:
            APIKeyUpdate(api_key="")
        
        assert "cannot be empty" in str(exc_info.value)


class TestEncryptionSecurity:
    """Test encryption/decryption security."""
    
    def test_encryption_decryption_cycle(self):
        """Test API key can be encrypted and decrypted correctly."""
        original_key = "AIzaSyC_test_encryption_key_33333567890"
        
        # Encrypt
        encrypted = encrypt_api_key(original_key)
        assert encrypted != original_key
        assert "$" in encrypted  # Contains salt separator
        
        # Decrypt
        decrypted = decrypt_api_key(encrypted)
        assert decrypted == original_key
    
    def test_different_encryptions_same_key(self):
        """Test same key encrypted twice produces different results (due to random salt)."""
        key = "AIzaSyC_test_randomness_key_44444567890"
        
        encrypted1 = encrypt_api_key(key)
        encrypted2 = encrypt_api_key(key)
        
        # Different ciphertexts due to random salt
        assert encrypted1 != encrypted2
        
        # But both decrypt to same value
        assert decrypt_api_key(encrypted1) == key
        assert decrypt_api_key(encrypted2) == key
    
    def test_invalid_encrypted_data_raises_error(self):
        """Test decryption fails gracefully on invalid data."""
        # decrypt_api_key returns None for invalid data (doesn't raise)
        result1 = decrypt_api_key("invalid-encrypted-data")
        assert result1 is None
        
        result2 = decrypt_api_key("no-dollar-sign")
        assert result2 is None
        
        result3 = decrypt_api_key("")
        assert result3 is None
    
    def test_encrypted_key_format(self):
        """Test encrypted key has expected format."""
        key = "AIzaSyC_test_format_key_1234567890123456"
        encrypted = encrypt_api_key(key)
        
        # Should have format: base64(salt)$ciphertext
        parts = encrypted.split("$")
        assert len(parts) == 2
        
        # Salt should be base64 encoded (16 bytes = 24 chars base64)
        salt_part = parts[0]
        assert len(salt_part) == 24  # 16 bytes base64 encoded
        
        # Ciphertext should exist
        ciphertext = parts[1]
        assert len(ciphertext) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
