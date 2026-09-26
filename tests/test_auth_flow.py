from app import create_app, db


def test_login_page_has_server_form_fields_and_logo():
    app = create_app()
    app.config['TESTING'] = True

    with app.test_client() as client:
        response = client.get('/login')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert 'name="login_input"' in html
        assert 'name="password"' in html
        assert 'logo.jpeg' in html


def test_signup_and_login_work_with_real_flask_forms():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        db.drop_all()
        db.create_all()

    with app.test_client() as client:
        signup = client.post(
            '/register',
            data={'username': 'newuser', 'email': 'new@demo.com', 'password': 'secret123'},
            follow_redirects=False,
        )
        assert signup.status_code in (302, 303)

        login = client.post(
            '/login',
            data={'login_input': 'newuser', 'password': 'secret123'},
            follow_redirects=True,
        )
        assert login.status_code == 200
        assert b'Operations dashboard' in login.data or b'Welcome back to StocVue.' in login.data
