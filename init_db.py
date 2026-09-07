from app import app, db, User

with app.app_context():
    db.create_all()

    # Clear existing users
    User.query.delete()

    # Create demo users
    admin = User(username='admin', role='admin')
    admin.set_password('admin123')

    user1 = User(username='security_manager', role='manager')
    user1.set_password('password123')

    user2 = User(username='staff', role='user')
    user2.set_password('password123')

    db.session.add(admin)
    db.session.add(user1)
    db.session.add(user2)
    db.session.commit()

    print("Database initialized with demo users:")
    print(" - admin / admin123")
    print(" - security_manager / password123")
    print(" - staff / password123")
    