from datetime import timedelta, datetime, timezone

import pytest

from app import create_app, db
from models import User, Song, friendships, ListeningEvent
from services.feed_service import get_friends_listening_now


@pytest.fixture
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def seed_users_and_friends(app):
    """Create users and friends. Some users will have listening events."""
    with app.app_context():

        # Create users
        users = [
            User(username=f"user{i}", email=f"user{i}@example.com")
            for i in range(1, 4)
        ]

        db.session.add_all(users)
        db.session.flush()

        # Create song
        song = Song(title=f"El Taxi", artist="Various", shared_by=users[0].id)

        db.session.add(song)
        db.session.flush()

        # Add friendships
        db.session.execute(friendships.insert().values(user_id=users[0].id, friend_id=users[1].id))
        db.session.execute(friendships.insert().values(user_id=users[0].id, friend_id=users[2].id))

        # Add listening events
        now = datetime.now(timezone.utc)

        # Recent listening event (last 10 min)
        recent_timestamp = now - timedelta(minutes=10)
        recent_event = ListeningEvent(user_id=users[1].id, song_id=song.id, listened_at=recent_timestamp)
        users[1].last_listened_at = recent_timestamp
        db.session.add(recent_event)

        # Old listening event (3 hrs ago)
        old_timestamp = now - timedelta(hours=3)
        old_event = ListeningEvent(user_id=users[2].id, song_id=song.id, listened_at=old_timestamp)
        users[2].last_listened_at = old_timestamp
        db.session.add(old_event)

        db.session.commit()
        yield {"user": users[0], "song": song}


def test_listening_now_returns_recent_events(app, seed_users_and_friends):
    """Only listening events from the last 30 minutes should be returned."""
    with app.app_context():

        user = seed_users_and_friends["user"].id
        feed = get_friends_listening_now(user)

        # There should only be ONE event from the last 30 min
        assert len(feed) == 1
