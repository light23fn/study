from flask import Flask, request, jsonify, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import os

app = Flask(__name__)

app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "None"

app.secret_key = "segredo123"

ADMIN_USER = "admin"

def get_db():
    return psycopg2.connect(
        os.environ.get("DATABASE_URL"),
        sslmode="require"
    )

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS resumos (
        id SERIAL PRIMARY KEY,
        titulo TEXT,
        conteudo TEXT,
        userr TEXT,
        materia TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS likes (
        id SERIAL PRIMARY KEY,
        resumo_id INTEGER,
        userr TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS comments (
        id SERIAL PRIMARY KEY,
        resumo_id INTEGER,
        userr TEXT,
        texto TEXT
    )
    """)

    conn.commit()
    conn.close()

# 🔐 REGISTER
@app.route("/register", methods=["POST"])
def register():
    data = request.json
    conn = get_db()
    c = conn.cursor()

    try:
        hashed = generate_password_hash(data["password"])

        c.execute("INSERT INTO users (username,password) VALUES (%s,%s)",
                  (data["username"], hashed))
        conn.commit()

    except Exception as e:
        print("ERRO REGISTER:", e)
        return jsonify({"error": "Erro ao criar conta"})
    
    conn.close()
    return jsonify({"status": "ok"})


# 🔐 LOGIN
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT password FROM users WHERE username=%s",
              (data["username"],))
    user = c.fetchone()

    conn.close()

    if user and check_password_hash(user[0], data["password"]):
        session["user"] = data["username"]
        return jsonify({"status": "ok"})

    return jsonify({"error": "Login inválido"})

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
    conn = get_db()
    c = conn.cursor()

    c.execute("INSERT INTO resumos (titulo,conteudo,userr,materia) VALUES (%s,%s,%s,%s)",
              (data["titulo"], data["conteudo"], session["user"], data["materia"]))

    conn.commit()
    conn.close()

    return jsonify({"status":"ok"})


# 📚 GET RESUMOS
@app.route("/resumos")
def resumos():
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT id,titulo,conteudo,userr,materia FROM resumos")
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
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT userr FROM resumos WHERE id=%s", (id,))
    r = c.fetchone()

    if not r:
        return jsonify({"error":"não existe"})

    if session["user"] != r[0] and session["user"] != ADMIN_USER:
        return jsonify({"error":"sem permissão"})

    c.execute("UPDATE resumos SET titulo=%s, conteudo=%s, materia=%s WHERE id=%s",
              (data["titulo"], data["conteudo"], data["materia"], id))

    conn.commit()
    conn.close()

    return jsonify({"status":"editado"})


# 🗑 DELETE RESUMO
@app.route("/delete/<int:id>", methods=["DELETE"])
def delete(id):
    if "user" not in session:
        return jsonify({"error":"login"})

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT userr FROM resumos WHERE id=%s", (id,))
    r = c.fetchone()

    if not r:
        return jsonify({"error":"não existe"})

    if session["user"] != r[0] and session["user"] != ADMIN_USER:
        return jsonify({"error":"sem permissão"})

    c.execute("DELETE FROM resumos WHERE id=%s", (id,))
    conn.commit()
    conn.close()

    return jsonify({"status":"apagado"})


# ❤️ LIKE
@app.route("/like", methods=["POST"])
def like():
    if "user" not in session:
        return jsonify({"error":"login"})

    data = request.json
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT * FROM likes WHERE resumo_id=%s AND userr=%s",
              (data["id"], session["user"]))

    if c.fetchone():
        c.execute("DELETE FROM likes WHERE resumo_id=%s AND userr=%s",
                  (data["id"], session["user"]))
    else:
        c.execute("INSERT INTO likes (resumo_id,userr) VALUES (%s,%s)",
                  (data["id"], session["user"]))

    conn.commit()
    conn.close()

    return jsonify({"status":"ok"})


# ❤️ CONTADOR
@app.route("/likes/<int:id>")
def get_likes(id):
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM likes WHERE resumo_id=%s", (id,))
    count = c.fetchone()[0]

    conn.close()
    return jsonify({"likes":count})


# 💬 GET COMMENTS
@app.route("/comments/<int:id>")
def comments(id):
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT id,userr,texto FROM comments WHERE resumo_id=%s", (id,))
    data = [{"id":r[0],"user":r[1],"texto":r[2]} for r in c.fetchall()]

    conn.close()
    return jsonify(data)


# 💬 ADD COMMENT
@app.route("/comment", methods=["POST"])
def comment():
    if "user" not in session:
        return jsonify({"error":"login"})

    data = request.json
    conn = get_db()
    c = conn.cursor()

    c.execute("INSERT INTO comments (resumo_id,userr,texto) VALUES (%s,%s,%s)",
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

    conn = get_db()
    c = conn.cursor()

    c.execute("DELETE FROM comments WHERE id=%s", (id,))
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
    conn = get_db()
    c = conn.cursor()

    c.execute("UPDATE comments SET texto=%s WHERE id=%s",
              (data["texto"], id))

    conn.commit()
    conn.close()

    return jsonify({"status":"ok"})

@app.route("/")
def home():
    return send_from_directory(".", "index.html")

@app.route("/dashboard")
def dashboard():
    return send_from_directory(".", "dash.html")

# STATIC
@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(".", path)

# RUN
import os

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))