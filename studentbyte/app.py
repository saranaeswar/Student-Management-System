from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import os

app = Flask(__name__)

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["studentbyte"]
students_col = db["students"]

def serialize(doc):
    doc["_id"] = str(doc["_id"])
    return doc

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/students", methods=["GET"])
def get_students():
    filter_type = request.args.get("filter", "all")
    query = {"status": "active"} if filter_type == "active" else {}
    docs = [serialize(d) for d in students_col.find(query).sort("created_at", -1)]
    return jsonify(docs)

@app.route("/api/students", methods=["POST"])
def add_student():
    data = request.json
    data["status"] = "active"
    data["created_at"] = datetime.utcnow().isoformat()
    result = students_col.insert_one(data)
    data["_id"] = str(result.inserted_id)
    return jsonify({"success": True, "student": data}), 201

@app.route("/api/students/<id>", methods=["PUT"])
def update_student(id):
    data = request.json
    data.pop("_id", None)
    students_col.update_one({"_id": ObjectId(id)}, {"$set": data})
    updated = serialize(students_col.find_one({"_id": ObjectId(id)}))
    return jsonify({"success": True, "student": updated})

@app.route("/api/students/<id>", methods=["DELETE"])
def delete_student(id):
    students_col.delete_one({"_id": ObjectId(id)})
    return jsonify({"success": True})

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
