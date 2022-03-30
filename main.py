from logging import debug
from flask import *
import sqlite3, hashlib, os
from werkzeug.utils import secure_filename
import time
from flaskext.mysql import MySQL

app = Flask(__name__)
app.secret_key = 'random string'
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = set(['jpeg', 'jpg', 'png', 'gif'])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
mysql = MySQL()
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'root'
app.config['MYSQL_DATABASE_DB'] = 'organic'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)



def getLoginDetails():
    with mysql.connect() as conn:
        cur = conn.cursor()
        if 'email' not in session:
            loggedIn = False
            firstName = ''
            noOfItems = 0
        else:
            loggedIn = True
            cur.execute('''SELECT userId, firstName FROM users WHERE email = %s''', (session['email'], ))
            userId, firstName = cur.fetchone()
            cur.execute('''SELECT count(productId) FROM kart WHERE userId = %s''', (userId, ))
            noOfItems = cur.fetchone()[0]
    return (loggedIn, firstName, noOfItems)

@app.route("/")
def root():
    loggedIn, firstName, noOfItems = getLoginDetails()
    with mysql.connect() as conn:
        cur = conn.cursor()
        cur.execute('''SELECT productId, name, price, description, image, stock FROM products''')
        itemData = cur.fetchall()
        cur.execute('''SELECT categoryId, name FROM categories''')
        categoryData = cur.fetchall()
  
    return render_template('home.html', itemData=itemData, loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems, categoryData=categoryData)

@app.route("/add")
def admin():
    with mysql.connect() as conn:
        cur = conn.cursor()
        cur.execute('''SELECT categoryId, name FROM categories''')
        categories = cur.fetchall()
    
    return render_template('add.html', categories=categories)

@app.route("/addItem", methods=["GET", "POST"])
def addItem():
    if request.method == "POST":
        name = request.form['name']
        price = float(request.form['price'])
        description = request.form['description']
        stock = int(request.form['stock'])
        categoryId = int(request.form['category'])

        #Uploading image procedure
        image = request.files['image']
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        imagename = filename
        with mysql.connect() as conn:
            try:
                cur = conn.cursor()
                cur.execute('''INSERT INTO products (name, price, description, image, stock, categoryId) VALUES (%s, %s, %s, %s, %s, %s)''', (name, price, description, imagename, stock, categoryId))
                conn.commit()
                msg="added successfully"
            except:
                msg="error occured"
                conn.rollback()
        
        print(msg)
        return redirect(url_for('root'))

@app.route("/removeItem")
def removeItem():
    productId = request.args.get('productId')
    with mysql.connect() as conn:
        try:
            cur = conn.cursor()
            cur.execute('''DELETE FROM products WHERE productID = %s''', (productId, ))
            conn.commit()
            msg = "Deleted successsfully"
        except:
            conn.rollback()
            msg = "Error occured"
    
    print(msg)
    return redirect(url_for('root'))

@app.route("/displayCategory")
def displayCategory():
        loggedIn, firstName, noOfItems = getLoginDetails()
        categoryId = request.args.get("categoryId")
        with mysql.connect() as conn:
            cur = conn.cursor()
            cur.execute('''SELECT products.productId, products.name, products.price, products.image, categories.name FROM products, categories WHERE products.categoryId = categories.categoryId AND categories.categoryId = %s''', (categoryId, ))
            data = cur.fetchall()
        
        categoryName = data[0][4]
        # data = parse(data)
        print(data)
        return render_template('displayCategory.html', data=data, loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems, categoryName=categoryName)

@app.route("/account/profile")
def profileHome():
    if 'email' not in session:
        return redirect(url_for('root'))
    loggedIn, firstName, noOfItems = getLoginDetails()
    with mysql.connect() as conn:
        cur = conn.cursor()
        cur.execute('''SELECT userId, email, firstName, lastName, address1, address2, zipcode, city, state, country, phone FROM users WHERE email = %s''', (session['email'], ))
        profileData = cur.fetchone()
    
    return render_template("profileHome.html",profileData=profileData, loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems)

@app.route("/account/profile/changePassword", methods=["GET", "POST"])
def changePassword():
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    if request.method == "POST":
        oldPassword = request.form['oldpassword']
        oldPassword = hashlib.md5(oldPassword.encode()).hexdigest()
        newPassword = request.form['newpassword']
        newPassword = hashlib.md5(newPassword.encode()).hexdigest()
        with mysql.connect() as conn:
            cur = conn.cursor()
            cur.execute('''SELECT userId, password FROM users WHERE email = %s''', (session['email'], ))
            userId, password = cur.fetchone()
            if (password == oldPassword):
                try:
                    cur.execute('''UPDATE users SET password = %s WHERE userId = %s''', (newPassword, userId))
                    conn.commit()
                    msg="Changed successfully"
                except:
                    conn.rollback()
                    msg = "Failed"
                return render_template("changePassword.html", msg=msg)
            else:
                msg = "Wrong password"
        
        return render_template("changePassword.html", msg=msg)
    else:
        return render_template("changePassword.html")

@app.route("/updateProfile", methods=["GET", "POST"])
def updateProfile():
    if request.method == 'POST':
        email = request.form['email']
        firstName = request.form['firstName']
        lastName = request.form['lastName']
        address1 = request.form['address1']
        address2 = request.form['address2']
        zipcode = request.form['zipcode']
        city = request.form['city']
        state = request.form['state']
        country = request.form['country']
        phone = request.form['phone']
        with mysql.connect() as con:
                try:
                    cur = con.cursor()
                    cur.execute('''UPDATE users SET firstName = %s, lastName = %s, address1 = %s, address2 = %s, zipcode = %s, city = %s, state = %s, country = %s, phone = %s WHERE email = %s''', (firstName, lastName, address1, address2, zipcode, city, state, country, phone, email))

                    con.commit()
                    msg = "Saved Successfully"
                except:
                    con.rollback()
                    msg = "Error occured"
        return redirect(url_for('profileHome'))

@app.route("/loginForm")
def loginForm():
    if 'email' in session:
        return redirect(url_for('root'))
    else:
        return render_template('login.html', error='')

@app.route("/login", methods = ['POST', 'GET'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if is_valid(email, password):
            session['email'] = email
            return redirect(url_for('root'))
        else:
            error = 'Invalid UserId / Password'
            return render_template('login.html', error=error)

@app.route("/productDescription")
def productDescription():
    loggedIn, firstName, noOfItems = getLoginDetails()
    productId = request.args.get('productId')
    with mysql.connect() as conn:
        cur = conn.cursor()
        cur.execute('''SELECT productId, name, price, description, image, stock FROM products WHERE productId = %s''', (productId, ))
        productData = cur.fetchone()
    
    return render_template("productDescription.html", data=productData, loggedIn = loggedIn, firstName = firstName, noOfItems = noOfItems)

@app.route("/addToCart")
def addToCart():
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    else:
        productId = int(request.args.get('productId'))
        with mysql.connect() as conn:
            cur = conn.cursor()
            cur.execute('''SELECT userId FROM users WHERE email = %s''', (session['email'], ))
            userId = cur.fetchone()[0]
            print("THe User", userId, "product", productId)
            try:
                cur.execute('''INSERT INTO kart (userId, productId) VALUES (%s, %s)''', (userId, productId))
                conn.commit()
                msg = "Added successfully"
                print(msg)
            except Exception as e:
                print("Errrrorrrr",e)
                conn.rollback()
                msg = "Error occured"
        
        return redirect(url_for('root'))

@app.route("/cart")
def cart():
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    loggedIn, firstName, noOfItems = getLoginDetails()
    email = session['email']
    with mysql.connect() as conn:
        cur = conn.cursor()
        cur.execute('''SELECT userId FROM users WHERE email = %s''', (email, ))
        userId = cur.fetchone()[0]
        cur.execute('''SELECT products.productId, products.name, products.price, products.image FROM products, kart WHERE products.productId = kart.productId AND kart.userId = %s''', (userId, ))
        products = cur.fetchall()
    totalPrice = 0
    for row in products:
        totalPrice += row[2]
    return render_template("cart.html", products = products, totalPrice=totalPrice, loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems)

@app.route("/removeFromCart")
def removeFromCart():
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    email = session['email']
    productId = int(request.args.get('productId'))
    with mysql.connect() as conn:
        cur = conn.cursor()
        cur.execute('''SELECT userId FROM users WHERE email = %s''', (email, ))
        userId = cur.fetchone()[0]
        try:
            cur.execute('''DELETE FROM kart WHERE userId = %s AND productId = %s''', (userId, productId))
            conn.commit()
            msg = "removed successfully"
        except:
            conn.rollback()
            msg = "error occured"
    
    return redirect(url_for('root'))

@app.route("/checkout")
def checkout():
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    loggedIn, firstName, noOfItems = getLoginDetails()
    email = session['email']
    with mysql.connect() as conn:
        cur = conn.cursor()
        cur.execute('''SELECT userId FROM users WHERE email = %s''', (email, ))
        userId = cur.fetchone()[0]
        cur.execute('''SELECT products.productId, products.name, products.price, products.image FROM products, kart WHERE products.productId = kart.productId AND kart.userId = %s''', (userId, ))
        products = cur.fetchall()
        print("-"*5, products)
    totalPrice = 0
    for row in products:
        totalPrice += row[2]
    return render_template('checkout.html', totalPrice=totalPrice, loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems)

@app.route("/payment", methods = ['GET', 'POST'])
def payment():
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    loggedIn, firstName, noOfItems = getLoginDetails()
    email = session['email']
    if request.method == "POST":
        name = request.form["cc-name"]
        number = request.form["cc-number"]
        date = request.form["cc-date"]
        cvv = request.form["cc-cvv"]
    
        with mysql.connect() as con:
                # try:
                cur = con.cursor()

                cur.execute('''SELECT userId FROM users WHERE email = %s''', (email, ))
                userId = cur.fetchone()[0]
                cur.execute('''SELECT products.productId, products.name, products.price, products.image FROM products, kart WHERE products.productId = kart.productId AND kart.userId = %s''', (userId, ))
                products = cur.fetchall()
                print(products)
                amount = 0
                for i in products:
                    amount += i[2]
                date = time.time()
                cur.execute('''INSERT INTO orders (amount, user_id, date) VALUES (%s, %s, %s)''', (amount, userId, date))
                con.commit()

                orderId = cur.lastrowid

                for product in products:
                    cur.execute('''INSERT INTO order_item (order_id, product_id) VALUES (%s, %s)''', (orderId, product[0]))
                    con.commit()
                    cur.execute('''DELETE FROM kart WHERE userId = %s AND productId = %s''', (userId, product[0]))
                    con.commit()

                cur.execute('''INSERT INTO cards (number, name, date, cvv) VALUES (%s, %s, %s, %s)''', (number, name, date, cvv))
                con.commit()
                msg = "Payment Successfully"
                # except Exception as e:
                #     con.rollback()
                #     msg = "Error occured"
                #     print("_"*5, e)
        return render_template("payment.html")

@app.route("/account/orders")
def orders():
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    loggedIn, firstName, noOfItems = getLoginDetails()
    email = session['email']
    with mysql.connect() as conn:
        cur = conn.cursor()
        cur.execute('''SELECT userId FROM users WHERE email = %s''', (email, ))
        userId = cur.fetchone()[0]
        cur.execute('''SELECT * FROM orders WHERE user_id = %s''', (userId, ))
        orders = cur.fetchall()
        user_orders = {}
        for o in orders:
            user_orders[o[0]] = {}
            cur.execute('''SELECT * FROM products WHERE productId IN (SELECT product_id FROM order_item WHERE order_id = %s )''', (o[0], ))
            items = cur.fetchall()
            user_orders[o[0]]["amount"] = o[1]
            items = " ".join(i[1] for i in items)
            user_orders[o[0]]["items"] = items
        print(user_orders)
    return render_template("orders.html", orders = user_orders, loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems)


@app.route("/logout")
def logout():
    session.pop('email', None)
    return redirect(url_for('root'))

def is_valid(email, password):
    con = mysql.connect()
    cur = con.cursor()
    cur.execute('''SELECT email, password FROM users''')
    data = cur.fetchall()
    for row in data:
        if row[0] == email and row[1] == hashlib.md5(password.encode()).hexdigest():
            return True
    return False

@app.route("/register", methods = ['GET', 'POST'])
def register():
    if request.method == 'POST':
        #Parse form data    
        password = request.form['password']
        email = request.form['email']
        firstName = request.form['firstName']
        lastName = request.form['lastName']
        address1 = request.form['address1']
        address2 = request.form['address2']
        zipcode = request.form['zipcode']
        city = request.form['city']
        state = request.form['state']
        country = request.form['country']
        phone = request.form['phone']

        with mysql.connect() as con:
            try:
                cur = con.cursor()
                cur.execute('''INSERT INTO users (password, email, firstName, lastName, address1, address2, zipcode, city, state, country, phone) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''', (hashlib.md5(password.encode()).hexdigest(), email, firstName, lastName, address1, address2, zipcode, city, state, country, phone))
                con.commit()
                msg = "Registered Successfully"
            except:
                con.rollback()
                msg = "Error occured"
        return render_template("login.html", error=msg)

@app.route("/registerationForm")
def registrationForm():
    return render_template("register.html")

@app.route("/superUser")
def superUser():
    with mysql.connect() as conn:
        cur = conn.cursor()
        cur.execute('''SELECT * FROM products''')
        products = cur.fetchall()
        cur.execute('''SELECT * FROM users''')
        users = cur.fetchall()
        cur.execute('''SELECT * FROM orders''')
        _orders = cur.fetchall()
        orders = {}
        for o in _orders:
            orders[o[0]] = {}
            cur.execute('''SELECT * FROM products WHERE productId IN (SELECT product_id FROM order_item WHERE order_id = %s )''', (o[0], ))
            items = cur.fetchall()
            items = " ".join(i[1] for i in items)
            orders[o[0]]["amount"] = o[1]
            orders[o[0]]["items"] = items
            cur.execute('''SELECT firstName, email, phone FROM users WHERE userId = %s''', (o[2],))
            user = cur.fetchone()
            orders[o[0]]["user"] = user
            orders[o[0]]["time"] = time.ctime(float(o[3]))

    print(orders)
    return render_template("admin.html", products = products, orders = orders, users = users)

def allowed_file(filename):
    return '.' in filename and \
            filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def parse(data):
    ans = []
    i = 0
    while i < len(data):
        curr = []
        for j in range(7):
            if i >= len(data):
                break
            curr.append(data[i])
            i += 1
        ans.append(curr)
    return ans

if __name__ == '__main__':
    app.run(debug=True)
