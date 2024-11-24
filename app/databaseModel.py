# User table (CRUD)
class UserTable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=True)

# Custom admin view for authentication
class MyAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return session.get("admin_logged_in")

    def inaccessible_callback(self, name, **kwargs):
        flash("Please log in as admin to access the admin panel.", "danger")
        return redirect(url_for("login"))

# Custom user table view (restrict access to admin)
class UserTableView(ModelView):
    def is_accessible(self):
        return session.get("admin_logged_in")

    def inaccessible_callback(self, name, **kwargs):
        flash("Please log in as admin to access the admin panel.", "danger")
        return redirect(url_for("login"))

# Add Flask-Admin with custom views
admin = Admin(app, index_view=MyAdminIndexView(), template_mode="bootstrap4")
admin.add_view(UserTableView(UserTable, db.session))

# Routes for login/logout
@app.route("/login/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        if email == os.getenv('ADMIN_EMAIL') and password == os.getenv('ADMIN_PASSWORD'):
            session["admin_logged_in"] = True
            flash("Login successful!", "success")
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid login. Please try again.", "danger")

    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Login</title>
        <link href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <div class="container">
            <div class="row justify-content-center mt-5">
                <div class="col-md-6">
                    <h2 class="text-center">Admin Login</h2>

                    <!-- Display Flash Messages -->
                    {% with messages = get_flashed_messages(with_categories=true) %}
                        {% if messages %}
                            <div class="alert alert-dismissible fade show mt-3" role="alert">
                                {% for category, message in messages %}
                                    <div class="alert alert-{{ category }} text-center">
                                        {{ message }}
                                    </div>
                                {% endfor %}
                            </div>
                        {% endif %}
                    {% endwith %}

                    <!-- Login Form -->
                    <form method="post">
                        <div class="form-group">
                            <label for="email">Email:</label>
                            <input type="email" class="form-control" id="email" name="email" required>
                        </div>
                        <div class="form-group">
                            <label for="password">Password:</label>
                            <input type="password" class="form-control" id="password" name="password" required>
                        </div>
                        <button type="submit" class="btn btn-primary btn-block">Login</button>
                    </form>
                </div>
            </div>
        </div>
    </body>
    </html>
    """)

# Admin Dashboard Route (for redirection after login)
@app.route("/admin/")
def admin_dashboard():
    return "<h1>Welcome to the Admin Dashboard</h1>"

@app.route("/logout/")
def logout():
    session.pop("admin_logged_in", None)
    flash("Logged out successfully.", "info")
    return redirect(url_for("login"))

# Ensure database tables are initialized
tables_initialized = False
@app.before_request
def create_tables():
    global tables_initialized
    if not tables_initialized:
        db.create_all()  # Create all tables
        tables_initialized = True  # Ensure this logic runs only once
