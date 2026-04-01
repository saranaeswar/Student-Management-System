from flask import Flask, render_template, request, jsonify
from sqlalchemy import create_engine, Column, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

app = Flask(__name__, template_folder='../templates', static_folder='../static')

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///students.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Student(Base):
    __tablename__ = "students"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    roll = Column(String, unique=True, index=True)
    phone = Column(String)
    email = Column(String)
    course = Column(String)
    department = Column(String)
    notes = Column(Text)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

# Test connection
try:
    db = get_db()
    db.execute("SELECT 1")
    print("Database connected successfully")
except Exception as e:
    print(f"Database connection failed: {e}")

def serialize(student):
    return {
        "_id": student.id,
        "name": student.name,
        "roll": student.roll,
        "phone": student.phone,
        "email": student.email,
        "course": student.course,
        "department": student.department,
        "notes": student.notes,
        "status": student.status,
        "created_at": student.created_at.isoformat() if student.created_at else None
    }

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/students", methods=["GET"])
def get_students():
    try:
        db = get_db()
        filter_type = request.args.get("filter", "all")
        query = db.query(Student)
        if filter_type == "active":
            query = query.filter(Student.status == "active")
        students = query.order_by(Student.created_at.desc()).all()
        return jsonify([serialize(s) for s in students])
    except Exception as e:
        print(f"Error in get_students: {e}")
        return jsonify({"error": "Database error"}), 500

@app.route("/api/students", methods=["POST"])
def add_student():
    try:
        data = request.json
        db = get_db()
        import uuid
        student = Student(
            id=str(uuid.uuid4()),
            name=data.get("name"),
            roll=data.get("roll"),
            phone=data.get("phone"),
            email=data.get("email"),
            course=data.get("course"),
            department=data.get("department"),
            notes=data.get("notes"),
            status="active",
            created_at=datetime.utcnow()
        )
        db.add(student)
        db.commit()
        db.refresh(student)
        return jsonify({"success": True, "student": serialize(student)}), 201
    except Exception as e:
        print(f"Error in add_student: {e}")
        return jsonify({"error": "Database error"}), 500

@app.route("/api/students/<id>", methods=["PUT"])
def update_student(id):
    try:
        data = request.json
        db = get_db()
        student = db.query(Student).filter(Student.id == id).first()
        if not student:
            return jsonify({"error": "Student not found"}), 404
        for key, value in data.items():
            if key != "_id" and hasattr(student, key):
                setattr(student, key, value)
        db.commit()
        db.refresh(student)
        return jsonify({"success": True, "student": serialize(student)})
    except Exception as e:
        print(f"Error in update_student: {e}")
        return jsonify({"error": "Database error"}), 500

@app.route("/api/students/<id>", methods=["DELETE"])
def delete_student(id):
    try:
        db = get_db()
        student = db.query(Student).filter(Student.id == id).first()
        if not student:
            return jsonify({"error": "Student not found"}), 404
        db.delete(student)
        db.commit()
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error in delete_student: {e}")
        return jsonify({"error": "Database error"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

@app.route("/api/dbms", methods=["POST"])
def dbms_console():
    sql = request.json.get("sql", "").strip()
    sql_upper = sql.upper().strip()
    result_msg = ""
    rows = []

    try:

        # ── DDL ──────────────────────────────────────────────────────────────

        # CREATE
        if sql_upper.startswith("CREATE"):
            # CREATE TABLE students (...) — we simulate by ensuring collection exists
            db.create_collection("students") if "students" not in db.list_collection_names() else None
            result_msg = "✅ CREATE: Collection 'students' is ready. (MongoDB creates collections automatically on first insert.)"

        # ALTER
        elif sql_upper.startswith("ALTER"):
            # ALTER TABLE students ADD COLUMN <field> <default>
            # e.g. ALTER TABLE students ADD COLUMN year 1
            parts = sql.split()
            if "ADD" in sql_upper and len(parts) >= 6:
                field   = parts[5]
                default = parts[6] if len(parts) > 6 else ""
                count   = students_col.update_many({}, {"$set": {field: default}}).modified_count
                result_msg = f"✅ ALTER: Added field '{field}' with default '{default}' to {count} record(s)."
            elif "DROP" in sql_upper and "COLUMN" in sql_upper and len(parts) >= 6:
                field = parts[5]
                count = students_col.update_many({}, {"$unset": {field: ""}}).modified_count
                result_msg = f"✅ ALTER: Removed field '{field}' from {count} record(s)."
            elif "RENAME" in sql_upper and "TO" in sql_upper:
                # ALTER TABLE students RENAME TO alumni
                new_name = parts[-1]
                students_col.rename(new_name)
                result_msg = f"✅ ALTER: Collection renamed to '{new_name}'."
            else:
                result_msg = "ℹ️ ALTER supported syntax:\n  ALTER TABLE students ADD COLUMN <field> <default>\n  ALTER TABLE students DROP COLUMN <field>\n  ALTER TABLE students RENAME TO <newname>"

        # DROP
        elif sql_upper.startswith("DROP"):
            students_col.drop()
            result_msg = "⚠️ DROP: Collection 'students' has been dropped. All records deleted."

        # TRUNCATE
        elif sql_upper.startswith("TRUNCATE"):
            count = students_col.count_documents({})
            students_col.delete_many({})
            result_msg = f"⚠️ TRUNCATE: Removed all {count} record(s) from 'students'. Collection still exists."

        # RENAME
        elif sql_upper.startswith("RENAME"):
            # RENAME TABLE students TO alumni
            parts = sql.split()
            if len(parts) >= 4 and "TO" in sql_upper:
                new_name = parts[-1]
                students_col.rename(new_name)
                result_msg = f"✅ RENAME: Collection renamed to '{new_name}'."
            else:
                result_msg = "ℹ️ RENAME syntax: RENAME TABLE students TO <newname>"

        # COMMENT
        elif sql_upper.startswith("COMMENT"):
            # COMMENT ON TABLE students IS 'some comment'
            result_msg = "ℹ️ COMMENT: MongoDB does not support native comments on collections, but your SQL comment has been noted."

        # ── DML ──────────────────────────────────────────────────────────────

        # SELECT
        elif sql_upper.startswith("SELECT"):
            query = {}

            # WHERE clause support (basic: field = 'value')
            if "WHERE" in sql_upper:
                where_part = sql[sql_upper.index("WHERE") + 5:].strip()
                # handle field = 'value' or field = value
                if "=" in where_part:
                    field, val = where_part.split("=", 1)
                    field = field.strip()
                    val   = val.strip().strip("'\"")
                    query = {field: val}

            # LIMIT support
            limit = 0
            if "LIMIT" in sql_upper:
                try:
                    limit = int(sql[sql_upper.index("LIMIT") + 5:].strip().split()[0])
                except:
                    limit = 0

            cursor = students_col.find(query)
            if limit:
                cursor = cursor.limit(limit)

            docs = [serialize(d) for d in cursor]
            rows = docs
            result_msg = f"✅ SELECT: Returned {len(docs)} record(s)."

        # INSERT
        elif sql_upper.startswith("INSERT"):
            # INSERT INTO students (name, roll) VALUES ('John', 'CS001')
            try:
                cols_part = sql[sql.index("(") + 1 : sql.index(")")]
                vals_part = sql[sql.rindex("(") + 1 : sql.rindex(")")]
                cols = [c.strip() for c in cols_part.split(",")]
                vals = [v.strip().strip("'\"") for v in vals_part.split(",")]
                doc  = dict(zip(cols, vals))
                doc["status"]     = "active"
                doc["created_at"] = datetime.utcnow().isoformat()
                students_col.insert_one(doc)
                result_msg = f"✅ INSERT: 1 record inserted with fields: {', '.join(cols)}."
            except Exception as e:
                result_msg = f"❌ INSERT failed: {e}\nSyntax: INSERT INTO students (name, roll) VALUES ('John', 'CS001')"

        # UPDATE
        elif sql_upper.startswith("UPDATE"):
            # UPDATE students SET field='value' WHERE field2='value2'
            try:
                set_part   = sql[sql_upper.index("SET") + 3:]
                query      = {}
                update_doc = {}
                if "WHERE" in sql_upper:
                    set_raw, where_raw = set_part.split("WHERE", 1) if "WHERE" in set_part.upper() else (set_part, "")
                    # parse SET
                    for pair in set_raw.split(","):
                        k, v = pair.split("=", 1)
                        update_doc[k.strip()] = v.strip().strip("'\"")
                    # parse WHERE
                    if "=" in where_raw:
                        k, v = where_raw.split("=", 1)
                        query[k.strip()] = v.strip().strip("'\"")
                else:
                    for pair in set_part.split(","):
                        k, v = pair.split("=", 1)
                        update_doc[k.strip()] = v.strip().strip("'\"")

                count = students_col.update_many(query, {"$set": update_doc}).modified_count
                result_msg = f"✅ UPDATE: {count} record(s) updated."
            except Exception as e:
                result_msg = f"❌ UPDATE failed: {e}\nSyntax: UPDATE students SET name='John' WHERE roll='CS001'"

        # DELETE
        elif sql_upper.startswith("DELETE"):
            # DELETE FROM students WHERE field='value'
            try:
                query = {}
                if "WHERE" in sql_upper:
                    where_part = sql[sql_upper.index("WHERE") + 5:].strip()
                    if "=" in where_part:
                        k, v   = where_part.split("=", 1)
                        query  = {k.strip(): v.strip().strip("'\"")}
                count = students_col.delete_many(query).deleted_count
                result_msg = f"✅ DELETE: {count} record(s) permanently deleted."
            except Exception as e:
                result_msg = f"❌ DELETE failed: {e}\nSyntax: DELETE FROM students WHERE roll='CS001'"

        # MERGE
        elif sql_upper.startswith("MERGE"):
            # MERGE: upsert by roll number
            # MERGE INTO students (name, roll) VALUES ('John', 'CS001')
            try:
                cols_part = sql[sql.index("(") + 1 : sql.index(")")]
                vals_part = sql[sql.rindex("(") + 1 : sql.rindex(")")]
                cols = [c.strip() for c in cols_part.split(",")]
                vals = [v.strip().strip("'\"") for v in vals_part.split(",")]
                doc  = dict(zip(cols, vals))
                doc["status"]     = "active"
                doc["created_at"] = datetime.utcnow().isoformat()
                key  = {"roll": doc.get("roll", "")}
                students_col.update_one(key, {"$set": doc}, upsert=True)
                result_msg = f"✅ MERGE: Record with roll '{doc.get('roll','')}' inserted or updated (upsert)."
            except Exception as e:
                result_msg = f"❌ MERGE failed: {e}\nSyntax: MERGE INTO students (name, roll) VALUES ('John', 'CS001')"

        # ── DCL ──────────────────────────────────────────────────────────────

        # GRANT
        elif sql_upper.startswith("GRANT"):
            # GRANT READ ON students TO user1
            parts = sql.split()
            priv  = parts[1] if len(parts) > 1 else "privilege"
            user  = parts[-1] if len(parts) > 3 else "user"
            result_msg = (
                f"✅ GRANT: '{priv}' privilege noted for user '{user}'.\n"
                f"ℹ️ To apply real MongoDB roles, use:\n"
                f"   db.createUser({{ user: '{user}', pwd: 'pass', roles: [{{ role: 'read', db: 'studentbyte' }}] }})"
            )

        # REVOKE
        elif sql_upper.startswith("REVOKE"):
            parts = sql.split()
            priv  = parts[1] if len(parts) > 1 else "privilege"
            user  = parts[-1] if len(parts) > 3 else "user"
            result_msg = (
                f"✅ REVOKE: '{priv}' privilege removed from user '{user}'.\n"
                f"ℹ️ To apply in MongoDB, use:\n"
                f"   db.revokeRolesFromUser('{user}', [{{ role: 'read', db: 'studentbyte' }}])"
            )

        # SHOW (bonus helper)
        elif sql_upper.startswith("SHOW"):
            cols = db.list_collection_names()
            result_msg = f"✅ SHOW: Collections in 'studentbyte' DB → {', '.join(cols) if cols else 'none'}"

        else:
            result_msg = (
                "❌ Unsupported command.\n\n"
                "DDL : CREATE, ALTER, DROP, TRUNCATE, RENAME, COMMENT\n"
                "DML : SELECT, INSERT, UPDATE, DELETE, MERGE\n"
                "DCL : GRANT, REVOKE\n"
                "EXTRA: SHOW"
            )

    except Exception as e:
        result_msg = f"❌ Error: {str(e)}"

    return jsonify({"message": result_msg, "rows": rows})


if __name__ == "__main__":
    app.run(debug=True)
