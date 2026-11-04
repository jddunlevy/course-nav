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
    # Real coursework from a DegreeWorks audit + unofficial transcript, under a
    # pseudonym. Grades are omitted: nothing reads completed_course.grade, so the
    # record carries no more than the product needs. Source PDFs are gitignored.
    ("Jordan Reyes", "jreyes@crimson.ua.edu", "Senior", "2024-2025",
     "Cognitive science"),
    ("Rosa Delgado", "rdelgado@crimson.ua.edu", "Sophomore", "2025",
     "Public health and storytelling"),
    ("Tobias Lindqvist", "tlindqvist@crimson.ua.edu", "Senior", "2023",
     "Environmental policy"),
]

# student index -> completed courses: (subject, number, title, term, grade, credits, [bucket codes])
COMPLETED = {
    0: [
        ("CS", "104", "Computer Science Principles", "AP", None, 3, []),
        ("EN", "101", "English Composition", "AP", None, 3, ['COMP']),
        ("EN", "102", "English Composition", "AP", None, 3, ['COMP']),
        ("GEO", "105", "Sustainable Earth", "AP", None, 4, ['NATSCI']),
        ("GY", "110", "Prin Human Geography", "AP", None, 3, ['SBS']),
        ("MATH", "125", "Calculus I", "AP", None, 4, ['MATH']),
        ("MATH", "126", "Calculus II", "AP", None, 4, ['MATH']),
        ("PH", "101", "General Physics I", "AP", None, 4, ['NATSCI']),
        ("PY", "101", "Intro to Psychology", "AP", None, 3, ['SBS']),
        ("ST", "260", "Statistical Data Analysis", "AP", None, 3, []),
        ("FR", "102", "French Language & Cultures II", "202530", None, 3, ['HUM', 'WLANG']),
        ("ECE", "121", "Intro to ECE", "202340", None, 1, []),
        ("ENGR", "123", "Engineering Foundations Honors", "202340", None, 3, []),
        ("EPIC", "101", "EPIC Freshman Seminar I", "202340", None, 1, []),
        ("FR", "201", "Intermediate French", "202340", None, 3, ['HUM', 'WLANG']),
        ("PH", "105", "General Physics W/Calc I", "202340", None, 4, ['NATSCI']),
        ("EC", "110", "Principles of Microeconomics", "202410", None, 3, ['SBS']),
        ("FR", "202", "Intermediate French", "202410", None, 3, ['HUM', 'WLANG']),
        ("GBA", "146", "Professional Development I", "202410", None, 1, ['COMPASS']),
        ("LGS", "201", "Honors Legal Env of Business", "202410", None, 3, []),
        ("MIS", "200", "Fundamentals of MIS", "202410", None, 3, []),
        ("AC", "210", "Intro To Accounting", "202440", None, 4, []),
        ("EC", "111", "Principles of Macroeconomics", "202440", None, 3, ['SBS']),
        ("FR", "323", "Persuasive & Analytical Writing", "202440", None, 3, ['W']),
        ("GBA", "246", "Professional Development II", "202440", None, 1, []),
        ("MGT", "300", "Org Theory & Behavior", "202440", None, 3, []),
        ("FR", "325", "Cultures and Conversations", "202510", None, 3, []),
        ("GBA", "300", "Business Communications", "202510", None, 3, ['W']),
        ("MIS", "221", "Business Programming I", "202510", None, 3, []),
        ("PSC", "361", "Fiscal Policy & Budget", "202510", None, 3, []),
        # HIST confirmed by the student's DegreeWorks audit, not by Banner:
        # the 2027 catalog tags SW 200 as Social & Behavioral only.
        ("SW", "200", "History Social Welfare US", "202510", None, 3, ['HIST', 'SBS']),
        ("UH", "205", "Found. of Community Engagement", "202510", None, 3, ['HUM']),
        ("ARH", "253", "Survey Of Art II", "202540", None, 3, []),
        ("EN", "253", "Literature and Genre", "202540", None, 3, ['HUM', 'LIT']),
        ("FR", "426", "History of the French Language", "202540", None, 3, []),
        ("GBA", "346", "Professional Development III", "202540", None, 1, []),
        ("MIS", "321", "Business Programming II", "202540", None, 3, []),
        ("MIS", "330", "Database Administration", "202540", None, 3, []),
        ("MKT", "300", "Marketing", "202540", None, 3, []),
        ("CS", "223", "Intro to Python Programming", "202610", None, 3, []),
        ("FR", "250", "Love & Transgression in FR Lit", "202610", None, 3, ['LIT']),
        ("MIS", "405", "Enterprise Network & Security", "202610", None, 3, []),
        ("MLC", "261", "Intro to Romance Linguistics", "202610", None, 3, []),
        ("NEW", "200", "Idea Lab", "202610", None, 3, []),
        ("OM", "300", "Intro Operations Management", "202610", None, 3, []),
        ("PSC", "370", "American Public Policy", "202610", None, 3, []),
        ("FI", "302", "Business Finance", "202630", None, 3, []),
        ("MIS", "497", "Special Topics", "202630", None, 3, []),
        ("EN", "321", "Essential Grammar", "202640", None, 3, []),
        ("FR", "421", "Pronunciation & Phonetics", "202640", None, 3, []),
        ("MIS", "430", "Systems Analysis & Design I", "202640", None, 3, []),
        ("MLC", "262", "Language and the Brain", "202640", None, 3, []),
        ("NEW", "213", "Honors Creativity", "202640", None, 4, ['ARTS', 'HUM']),
        ("NEW", "407", "Landscapes of the South", "202640", None, 3, []),
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
    # Child rows first. search_request.actor_user_id references app_user, so
    # re-seeding after anyone has run a search fails on a FK constraint
    # without these three deletes.
    conn.execute("DELETE FROM recommendation_bucket")
    conn.execute("DELETE FROM recommendation")
    conn.execute("DELETE FROM search_request")
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
