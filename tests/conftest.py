"""
tests/conftest.py - Pytest Fixtures & Test Setup
=================================================
Provides reusable test fixtures:
- Flask test client
- Authenticated admin client
- Authenticated operator client
- Synthetic normal and defective test image fixtures
"""

import os
import sys
import tempfile
import pytest
import numpy as np

# Ensure root and src are on path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT_DIR, "src")
FIXTURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
os.makedirs(FIXTURES_DIR, exist_ok=True)

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# Generate synthetic fixtures if missing
NORMAL_FIXTURE_PATH = os.path.join(FIXTURES_DIR, "normal.png")
DEFECTIVE_FIXTURE_PATH = os.path.join(FIXTURES_DIR, "defective_crack.png")

try:
    import cv2
    # Create clean machined disk image
    if not os.path.exists(NORMAL_FIXTURE_PATH):
        img_norm = np.full((256, 256, 3), 40, dtype=np.uint8)
        cv2.circle(img_norm, (128, 128), 90, (180, 180, 185), -1)
        cv2.circle(img_norm, (128, 128), 35, (40, 40, 40), -1)
        cv2.imwrite(NORMAL_FIXTURE_PATH, img_norm)

    # Create machined disk with prominent synthetic crack
    if not os.path.exists(DEFECTIVE_FIXTURE_PATH):
        img_def = np.full((256, 256, 3), 40, dtype=np.uint8)
        cv2.circle(img_def, (128, 128), 90, (180, 180, 185), -1)
        cv2.circle(img_def, (128, 128), 35, (40, 40, 40), -1)
        # Jagged crack line
        pts = np.array([[128, 80], [135, 105], [126, 125], [142, 145], [138, 170]], np.int32)
        cv2.polylines(img_def, [pts], isClosed=False, color=(20, 20, 20), thickness=3)
        cv2.imwrite(DEFECTIVE_FIXTURE_PATH, img_def)
except Exception:
    pass


@pytest.fixture
def fixtures_dir():
    return FIXTURES_DIR


@pytest.fixture
def normal_image_path():
    return NORMAL_FIXTURE_PATH


@pytest.fixture
def defective_image_path():
    return DEFECTIVE_FIXTURE_PATH


@pytest.fixture
def test_app():
    from app import app
    from models import DatabaseManager

    # Use a temporary SQLite database for isolated test execution
    temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    temp_db.close()

    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False

    # Point models singleton to test database
    import models
    original_db = models.db
    models.db = DatabaseManager(db_path=temp_db.name)

    yield app

    # Cleanup
    models.db = original_db
    if os.path.exists(temp_db.name):
        try:
            os.remove(temp_db.name)
        except OSError:
            pass


@pytest.fixture
def client(test_app):
    """Unauthenticated test client."""
    return test_app.test_client()


@pytest.fixture
def admin_client(test_app):
    """Authenticated test client logged in as 'admin'."""
    client = test_app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["username"] = "admin"
        sess["role"] = "admin"
    return client


@pytest.fixture
def operator_client(test_app):
    """Authenticated test client logged in as 'operator'."""
    client = test_app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = 2
        sess["username"] = "operator"
        sess["role"] = "operator"
    return client
