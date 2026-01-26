"""Tests for authentication routes."""
import pytest


class TestLogin:
    def test_login_page_loads(self, client):
        """Test that login page loads."""
        response = client.get('/login/')
        assert response.status_code == 200
        assert b'Libriya' in response.data

    def test_successful_login(self, client, admin_user):
        """Test successful login."""
        response = client.post('/login/', data={
            'username': 'admin_test',
            'password': 'password'
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'Login successful!' in response.data

    def test_invalid_login(self, client):
        """Test login with invalid credentials."""
        response = client.post('/login/', data={
            'username': 'nonexistent',
            'password': 'wrong'
        }, follow_redirects=True)
        assert b'Invalid username or password' in response.data

    def test_logout(self, client, admin_user):
        """Test logout."""
        client.post('/login/', data={
            'username': 'admin_test',
            'password': 'password'
        })
        response = client.get('/logout', follow_redirects=True)
        assert b'logged out' in response.data
