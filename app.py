from flask import Flask, request, jsonify, session, send_from_directory
import sqlite3

app = Flask(__name__)
app.secret_key = "segredo123"

ADMIN_USER = "admin"

def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS resumos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT,
        conteudo TEXT,
        user TEXT,
        materia TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS likes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        resumo_id INTEGER,
        user TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        resumo_id INTEGER,
        user TEXT,
        texto TEXT
    )''')

    conn.commit()
    conn.close()

# 🔐 REGISTER
@app.route("/register", methods=["POST"])
def register():
    data = request.json
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    try:
        c.execute("INSERT INTO users VALUES (NULL,?,?)",
                  (data["username"], data["password"]))
        conn.commit()
    except:
        return jsonify({"error":"User existe"})

    conn.close()
    return jsonify({"status":"ok"})

# 🔐 LOGIN
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE username=? AND password=?",
              (data["username"], data["password"]))
    user = c.fetchone()

    conn.close()

    if user:
        session["user"] = data["username"]
        return jsonify({"status":"ok"})
    return jsonify({"error":"Login inválido"})

# 👤 USER
@app.route("/me")
def me():
    return jsonify({"user": session.get("user")})

# ➕ ADD RESUMO (COM MATÉRIA)
@app.route("/add", methods=["POST"])
def add():
    if "user" not in session:
        return jsonify({"error":"login"})

    data = request.json
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("INSERT INTO resumos VALUES (NULL,?,?,?,?)",
              (data["titulo"], data["conteudo"], session["user"], data["materia"]))

    conn.commit()
    conn.close()

    return jsonify({"status":"ok"})

# 📚 GET RESUMOS
@app.route("/resumos")
def resumos():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT id,titulo,conteudo,user,materia FROM resumos")
    resumos = [{
        "id":r[0],
        "titulo":r[1],
        "conteudo":r[2],
        "user":r[3],
        "materia":r[4]
    } for r in c.fetchall()]

    conn.close()

    return jsonify({
        "resumos": resumos,
        "user": session.get("user")
    })

# ✏️ EDIT RESUMO (COM MATÉRIA)
@app.route("/edit/<int:id>", methods=["POST"])
def edit(id):
    if "user" not in session:
        return jsonify({"error":"login"})

    data = request.json
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT user FROM resumos WHERE id=?", (id,))
    r = c.fetchone()

    if not r:
        return jsonify({"error":"não existe"})

    if session["user"] != r[0] and session["user"] != ADMIN_USER:
        return jsonify({"error":"sem permissão"})

    c.execute("UPDATE resumos SET titulo=?, conteudo=?, materia=? WHERE id=?",
              (data["titulo"], data["conteudo"], data["materia"], id))

    conn.commit()
    conn.close()

    return jsonify({"status":"editado"})

# 🗑 DELETE RESUMO
@app.route("/delete/<int:id>", methods=["DELETE"])
def delete(id):
    if "user" not in session:
        return jsonify({"error":"login"})

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT user FROM resumos WHERE id=?", (id,))
    r = c.fetchone()

    if not r:
        return jsonify({"error":"não existe"})

    if session["user"] != r[0] and session["user"] != ADMIN_USER:
        return jsonify({"error":"sem permissão"})

    c.execute("DELETE FROM resumos WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return jsonify({"status":"apagado"})

# ❤️ LIKE
@app.route("/like", methods=["POST"])
def like():
    if "user" not in session:
        return jsonify({"error":"login"})

    data = request.json
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT * FROM likes WHERE resumo_id=? AND user=?",
              (data["id"], session["user"]))

    if c.fetchone():
        c.execute("DELETE FROM likes WHERE resumo_id=? AND user=?",
                  (data["id"], session["user"]))
    else:
        c.execute("INSERT INTO likes VALUES (NULL,?,?)",
                  (data["id"], session["user"]))

    conn.commit()
    conn.close()

    return jsonify({"status":"ok"})

# ❤️ CONTADOR
@app.route("/likes/<int:id>")
def get_likes(id):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM likes WHERE resumo_id=?", (id,))
    count = c.fetchone()[0]

    conn.close()
    return jsonify({"likes":count})

# 💬 GET COMMENTS
@app.route("/comments/<int:id>")
def comments(id):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT id,user,texto FROM comments WHERE resumo_id=?", (id,))
    data = [{"id":r[0],"user":r[1],"texto":r[2]} for r in c.fetchall()]

    conn.close()
    return jsonify(data)

# 💬 ADD COMMENT
@app.route("/comment", methods=["POST"])
def comment():
    if "user" not in session:
        return jsonify({"error":"login"})

    data = request.json
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("INSERT INTO comments VALUES (NULL,?,?,?)",
              (data["id"], session["user"], data["texto"]))

    conn.commit()
    conn.close()

    return jsonify({"status":"ok"})

# 🗑 DELETE COMMENT (ADMIN)
@app.route("/delete_comment/<int:id>", methods=["DELETE"])
def delete_comment(id):
    if "user" not in session:
        return jsonify({"error":"login"})

    if session["user"] != ADMIN_USER:
        return jsonify({"error":"sem permissão"})

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("DELETE FROM comments WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return jsonify({"status":"ok"})

# ✏️ EDIT COMMENT (ADMIN)
@app.route("/edit_comment/<int:id>", methods=["POST"])
def edit_comment(id):
    if "user" not in session:
        return jsonify({"error":"login"})

    if session["user"] != ADMIN_USER:
        return jsonify({"error":"sem permissão"})

    data = request.json
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("UPDATE comments SET texto=? WHERE id=?",
              (data["texto"], id))

    conn.commit()
    conn.close()

    return jsonify({"status":"ok"})

# STATIC
@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(".", path)

# RUN
if __name__ == "__main__":
    init_db()
    app.run(debug=True)