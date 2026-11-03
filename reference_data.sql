-- Reference data: the gen-ed bucket allowlist and the requirement stack.
--
-- Source of truth: Pre-Advising Checklist, rev. Nov 2025, p.2
--   (MIS 430/final-project/reference/PRE-Advising-Checklist-new-catalog.pdf)
-- Counts in comments are spring2027.csv section counts, for sanity checks.
--
-- D-28: 12 of Banner's 26 section attributes are gen-ed buckets. The other 14
-- are program or administrative tags and are deliberately excluded:
--   PW: Global Engagement (768), PW: Executive Systems (337),
--   PW: Digital Literacy & Pract (220), PW: Innovation and Creativity (191),
--   Experiential Learning (804), Virtual Private Network Enable (315),
--   University Honors (277), CBA International Course Req (225),
--   Computer Science (201), Special Topics Course (926),
--   Cooperative Education (15), UA-Huntsville Course (3),
--   Dining Dollars Exempt (2), Pract (join artefact, now fixed upstream).
--
-- 'Computer Science' is excluded on purpose: it appears nowhere in the NC
-- checklist, so it is another college's core requirement.
-- 'Special Topics Course' is excluded as a BUCKET but is read at ingest to set
-- course_offering.is_special_topics (D-21 / D-27).

INSERT INTO gen_ed_bucket (code, banner_attribute, name) VALUES
    ('NATSCI',  'Natural Science',                 'Natural Science'),          -- 377
    ('HUM',     'Humanities',                      'Humanities'),               -- 589
    ('LIT',     'Literature',                      'Literature'),               -- 250
    ('ARTS',    'Fine Arts',                       'Fine Arts'),                --  73
    ('WLANG',   'World Language',                  'World Language'),           --  94
    ('HIST',    'History',                         'History'),                  -- 176
    ('SBS',     'Social and Behavioral Sciences',  'Social & Behavioral Sciences'), -- 300
    ('W',       'Writing',                         'Writing (W)'),              -- 482
    ('USGC',    'US and Global Citizenship',       'US & Global Citizenship'),  -- 149
    ('MATH',    'Mathematical Science',            'Mathematical Science'),     -- 128
    ('COMP',    'Written Composition',             'Written Composition'),      -- 218
    ('COMPASS', 'First-Year Compass',              'First-Year Compass');       -- 294


-- Bucket-driven requirements. These are what D-19 ranks against.
INSERT INTO requirement
    (code, name, system, rule_kind, hours_needed, min_courses, lab_hours_needed, min_course_level, note)
VALUES
    ('CORE_NATSCI', 'Natural Sciences', 'core', 'bucket', 8, NULL, 2, NULL,
     '8 hours with at least two hours of lab. Lab is detected from schedule_type, not attributes.'),

    ('CORE_HUM', 'Humanities, Literature, Fine Arts & World Language', 'core', 'bucket', 9, NULL, 0, NULL,
     '9 hours across the pool, including at least one Literature course.'),

    ('CORE_SOC', 'History & Social/Behavioral Sciences', 'core', 'bucket', 9, NULL, 0, NULL,
     '9 hours across the pool, including at least one History course.'),

    ('CORE_MATH', 'Mathematics', 'core', 'bucket', NULL, 1, 0, NULL,
     'MATH 110 at a minimum. MATH 125 is required for BS degrees.'),

    ('CORE_COMP', 'First-Year Composition', 'core', 'bucket', 6, NULL, 0, NULL,
     'EN 101 / 102 / 103.'),

    ('CORE_COMPASS', 'Legends & College Compass', 'core', 'bucket', NULL, 1, 0, NULL,
     'First-year Legends and college-specific Compass, e.g. NEW 101.'),

    ('UNIV_W', 'Writing (W) course', 'university', 'bucket', 3, NULL, 0, NULL,
     'One 3-hour W class.'),

    ('UNIV_USGC', 'US & Global Citizenship', 'university', 'bucket', 3, NULL, 0, NULL,
     'One 3-hour USGC class.'),

    ('UNIV_WLANG', 'World Language', 'university', 'bucket', NULL, 1, 0, NULL,
     'NC students must fulfil UA''s World Language requirement. Also counts toward CORE_HUM -- a genuine double count (D-19).');


-- Numeric requirements. Displayed as progress; never ranked on.
INSERT INTO requirement
    (code, name, system, rule_kind, hours_needed, min_courses, lab_hours_needed, min_course_level, note)
VALUES
    ('UNIV_TOTAL', 'Total eligible hours', 'university', 'numeric', 120, NULL, 0, NULL,
     'Excludes duplicate classes and some activity hours.'),
    ('UNIV_UPPER', 'Hours at 300 level or above', 'university', 'numeric', 36, NULL, 0, 300, NULL),
    ('NC_DEPTH', 'Depth study hours', 'new_college', 'numeric', 33, NULL, 0, NULL,
     'Minimum 33 hours.'),
    ('NC_DEPTH_UPPER', 'Depth study hours at 300/400', 'new_college', 'numeric', 15, NULL, 0, 300, NULL);

-- D-23: NEW seminar themes (CC / ESC / SPSC) are deliberately absent. Banner has
-- no attribute for them and NC's list is still being compiled (F-36).


-- Requirement -> bucket union (D-28).
INSERT INTO requirement_bucket (requirement_id, bucket_id, is_must_include, min_hours)
SELECT r.requirement_id, b.bucket_id, x.must, x.min_hours
FROM (
    SELECT 'CORE_NATSCI'  AS rc, 'NATSCI'  AS bc, 0 AS must, NULL AS min_hours
    UNION ALL SELECT 'CORE_HUM',     'HUM',     0, NULL
    UNION ALL SELECT 'CORE_HUM',     'LIT',     1, 3     -- "including at least one Literature"
    UNION ALL SELECT 'CORE_HUM',     'ARTS',    0, NULL
    UNION ALL SELECT 'CORE_HUM',     'WLANG',   0, NULL
    UNION ALL SELECT 'CORE_SOC',     'HIST',    1, 3     -- "including at least one History"
    UNION ALL SELECT 'CORE_SOC',     'SBS',     0, NULL
    UNION ALL SELECT 'CORE_MATH',    'MATH',    0, NULL
    UNION ALL SELECT 'CORE_COMP',    'COMP',    0, NULL
    UNION ALL SELECT 'CORE_COMPASS', 'COMPASS', 0, NULL
    UNION ALL SELECT 'UNIV_W',       'W',       0, NULL
    UNION ALL SELECT 'UNIV_USGC',    'USGC',    0, NULL
    UNION ALL SELECT 'UNIV_WLANG',   'WLANG',   0, NULL
) x
JOIN requirement   r ON r.code = x.rc
JOIN gen_ed_bucket b ON b.code = x.bc;
