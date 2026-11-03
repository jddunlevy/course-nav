"""Seed demo advisors, students and completed coursework.

D-24: completed coursework comes from DegreeWorks. The import mechanism is still
an open item (audit-PDF parse vs manual entry), so the prototype runs on seeded
data. completed_course_bucket records what each course COUNTED FOR, because
DegreeWorks is the authority on that (F-19) and we cannot re-derive a 2024
course's attributes from the spring 2027 catalog.

    python seed.py
"""

import db

ADVISORS = [
    ("Dana Whitfield", "dwhitfield@ua.edu"),
]

# (name, email, classification, catalog_year, depth_study_label)
STUDENTS = [
    ("Avery Nkemdirim", "ankemdirim@crimson.ua.edu", "Junior", "2024",
     "Aerospace engineering & entrepreneurship"),
    ("Rosa Delgado", "rdelgado@crimson.ua.edu", "Sophomore", "2025",
     "Public health and storytelling"),
    ("Tobias Lindqvist", "tlindqvist@crimson.ua.edu", "Senior", "2023",
     "Environmental policy"),
]

# student index -> completed courses: (subject, number, title, term, grade, credits, [bucket codes])
COMPLETED = {
    0: [
        ("EN", "101", "English Composition I", "202340", "A", 3, ["COMP"]),
        ("EN", "102", "English Composition II", "202410", "A", 3, ["COMP"]),
        ("NEW", "101", "New College Compass", "202340", "A", 1, ["COMPASS"]),
        ("MATH", "125", "Calculus I", "202340", "B", 4, ["MATH"]),
        ("PH", "105", "General Physics I", "202410", "B", 4, ["NATSCI"]),
        ("HY", "101", "Western Civilisation I", "202410", "A", 3, ["HIST"]),
        ("NEW", "200", "Idea Lab", "202440", "A", 3, []),
        # outstanding: CORE_HUM (all 9), CORE_NATSCI (4 more + lab),
        #              CORE_SOC (6 more), UNIV_W, UNIV_USGC, UNIV_WLANG
    ],
    1: [
        ("EN", "101", "English Composition I", "202440", "A", 3, ["COMP"]),
        ("NEW", "101", "New College Compass", "202440", "B", 1, ["COMPASS"]),
        ("MATH", "110", "Finite Mathematics", "202440", "B", 3, ["MATH"]),
        ("BSC", "114", "Principles of Biology I", "202510", "A", 4, ["NATSCI"]),
        ("BSC", "115", "Principles of Biology I Lab", "202510", "A", 1, ["NATSCI"]),
        # outstanding: most of it -- a good demo of a wide-open student
    ],
    2: [
        ("EN", "101", "English Composition I", "202240", "A", 3, ["COMP"]),
        ("EN", "102", "English Composition II", "202310", "A", 3, ["COMP"]),
        ("NEW", "101", "New College Compass", "202240", "A", 1, ["COMPASS"]),
        ("MATH", "110", "Finite Mathematics", "202240", "A", 3, ["MATH"]),
        ("GY", "101", "Atmospheric Processes", "202310", "A", 3, ["NATSCI"]),
        ("GY", "102", "Atmospheric Processes Lab", "202310", "A", 1, ["NATSCI"]),
        ("GY", "105", "Earth Surface Processes", "202340", "B", 4, ["NATSCI"]),
        ("PSC", "101", "Intro to American Politics", "202310", "A", 3, ["SBS"]),
        ("PSC", "203", "Intro to Comparative Politics", "202340", "A", 3, ["SBS"]),
        ("HY", "135", "American Civilisation", "202410", "B", 3, ["HIST"]),
        ("SPA", "101", "Elementary Spanish I", "202410", "B", 4, ["WLANG", "HUM"]),
        ("SPA", "102", "Elementary Spanish II", "202440", "B", 4, ["WLANG", "HUM"]),
        ("PHL", "100", "Intro to Philosophy", "202440", "A", 3, ["HUM"]),
        # outstanding: CORE_HUM needs its Literature course, plus W and USGC
    ],
}


def run(conn):
    bids = {r["code"]: r["bucket_id"]
            for r in conn.execute("SELECT code, bucket_id FROM gen_ed_bucket")}

    advisor_ids = []
    for name, email in ADVISORS:
        cur = conn.execute("INSERT INTO advisor (name, email) VALUES (?, ?)",
                           (name, email))
        advisor_ids.append(cur.lastrowid)
        conn.execute(
            "INSERT INTO app_user (username, display_name, role, advisor_id)"
            " VALUES (?, ?, 'advisor', ?)",
            (email.split("@")[0], name, cur.lastrowid))

    for i, (name, email, classification, year, depth) in enumerate(STUDENTS):
        cur = conn.execute("""
            INSERT INTO student
                (name, email, classification, catalog_year, advisor_id, depth_study_label)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, email, classification, year, advisor_ids[0], depth))
        sid = cur.lastrowid
        conn.execute(
            "INSERT INTO app_user (username, display_name, role, student_id)"
            " VALUES (?, ?, 'student', ?)",
            (email.split("@")[0], name, sid))

        for subj, num, title, term, grade, credits, buckets in COMPLETED.get(i, []):
            cur = conn.execute("""
                INSERT INTO completed_course
                    (student_id, subject, course_number, title, term, grade, credits)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (sid, subj, num, title, term, grade, credits))
            for b in buckets:
                conn.execute(
                    "INSERT INTO completed_course_bucket (completed_id, bucket_id)"
                    " VALUES (?, ?)", (cur.lastrowid, bids[b]))

    conn.commit()


if __name__ == "__main__":
    conn = db.connect()
    conn.execute("DELETE FROM completed_course_bucket")
    conn.execute("DELETE FROM completed_course")
    conn.execute("DELETE FROM app_user")
    conn.execute("DELETE FROM student")
    conn.execute("DELETE FROM advisor")
    run(conn)
    for r in conn.execute("SELECT s.name, s.classification, a.name AS advisor,"
                          " (SELECT COUNT(*) FROM completed_course c"
                          "  WHERE c.student_id = s.student_id) AS done"
                          " FROM student s LEFT JOIN advisor a USING (advisor_id)"):
        print("{:22s} {:10s} advisor {:18s} {} completed".format(
            r["name"], r["classification"], r["advisor"], r["done"]))
