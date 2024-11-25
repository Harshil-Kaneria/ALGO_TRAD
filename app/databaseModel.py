# User table (CRUD)
class UserTable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    number = db.Column(db.String(15), nullable=False)
    loginPin = db.Column(db.String(6), nullable=False, default=lambda: ''.join(random.choices(string.digits, k=6)))
    type = db.Column(db.String(10), nullable=False, default='isPAID')  # can be 'isVIP' or 'isPAID'
    session_token = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f'<User {self.name}>'

# Custom admin view for authentication
class MyAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        total_users = UserTable.query.count()
        total_paid_users = UserTable.query.filter_by(type='isPAID').count()
        total_vip_users = UserTable.query.filter_by(type='isVIP').count()

        return self.render('admin/index.html', 
                           total_users=total_users, 
                           total_paid_users=total_paid_users, 
                           total_vip_users=total_vip_users)

    def is_visible(self):
        # This view won't appear in the menu structure
        return False

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
admin = Admin(app,name="Smart AI Trading Admin",index_view=MyAdminIndexView(), template_mode="bootstrap4")
admin.add_view(UserTableView(UserTable, db.session))
admin.add_link(MenuLink(name="Logout", url="/logout"))

# Routes for login/logout
@app.route("/login/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        if email == os.getenv('ADMIN_EMAIL') and password == os.getenv('ADMIN_PASSWORD'):
            session["admin_logged_in"] = True
            flash("Login successful!", "success")
            return redirect('/admin/usertable')
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
                        <button type="submit" class="btn btn-outline-success btn-block">Login</button>
                    </form>
                </div>
            </div>
        </div>
    </body>
    </html>
    """)

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
