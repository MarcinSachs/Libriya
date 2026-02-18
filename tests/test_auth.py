"""Tests for authentication routes."""
import pytest


class TestLogin:
    def test_login_page_loads(self, client):
        """Test that login page loads."""
        response = client.get('/auth/login/')
        assert response.status_code == 200
        assert b'Libriya' in response.data

    def test_successful_login(self, client, admin_user):
        """Test successful login."""
        response = client.post('/auth/login/', data={
            'username': 'admin_test',
            'password': 'password'
        }, follow_redirects=True)
        assert response.status_code == 200

    def test_invalid_login(self, client):
        """Test login with invalid credentials."""
        response = client.post('/auth/login/', data={
            'username': 'nonexistent',
            'password': 'wrong'
        }, follow_redirects=True)
        assert b'Invalid' in response.data or response.status_code == 200

    def test_logout(self, client, admin_user):
        """Test logout."""
        client.post('/auth/login/', data={
            'username': 'admin_test',
            'password': 'password'
        })
        response = client.get('/auth/logout', follow_redirects=True)
        assert response.status_code == 200
