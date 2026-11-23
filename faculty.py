"""
The department's faculty members, and who teaches which 5th-semester course.

Source: the department booklet (Faculty Members pages), corrected by
Nabiha where it is out of date: the chairman is now Dr. Kazi Tanvir Ahmmed,
and teachers who are teaching this semester are not marked as on leave.
Edit this file when anything changes; the website reads it at start-up.
"""

CHAIRMAN = "Dr. Kazi Tanvir Ahmmed"

# (name, designation, email, on study leave)
FACULTY = [
    ("Dr. Kazi Tanvir Ahmmed",          "Professor",           "tanvir@cu.ac.bd",            False),
    ("Dr. Md. Fazlul Kader",            "Professor",           "fkader@cu.ac.bd",            False),
    ("Dr. Jamal Uddin Ahamed",          "Professor",           "ahamed.jamal@cu.ac.bd",      False),
    ("Dr. Hasan Khaled Rouf",           "Professor",           "hasan.rouf@cu.ac.bd",        False),
    ("Dr. Mohammad Abdul Alim",         "Professor",           "mohammadabdulalim@cu.ac.bd", False),
    ("Dr. Mohammad Arif Iftakher Mahmood", "Professor",        "arif.iftakher@gmail.com",    False),
    ("Dr. Md. Murshadul Hoque",         "Professor",           "m.hoque@cu.ac.bd",           False),
    ("Dr. Md. Shah Alam",               "Professor",           "shah.alam@cu.ac.bd",         False),
    ("Dr. Mohammad Shuhrawardy",        "Associate Professor", "mswardy@cu.ac.bd",           False),
    ("Dr. Ariful Islam",                "Associate Professor", "ariful@cu.ac.bd",            False),
    ("S. M. Abu Zahed Chowdhury",       "Associate Professor", "zahed_apece@cu.ac.bd",       False),
    ("Sabrina Alam",                    "Associate Professor", "sabrina.apece@cu.ac.bd",     False),
    ("Saumitra Kumar Kuri",             "Associate Professor", "skkuri@cu.ac.bd",            False),
    ("Sabuj Chowdhury",                 "Assistant Professor", "sabuj.apece@cu.ac.bd",       False),
    ("Md. Didarul Alam",                "Assistant Professor", "didar.apece@cu.ac.bd",       True),
    ("Dr. Mohammad Shah Alamgir",       "Assistant Professor", "shah_a@cu.ac.bd",            True),
    ("Alamgir Hossain",                 "Assistant Professor", "ah.apece@cu.ac.bd",          True),
    ("Md. Shariful Islam",              "Assistant Professor", "shariful2488@cu.ac.bd",      False),
    ("Tauhidul Haque",                  "Assistant Professor", "tauhidulhaque@cu.ac.bd",     True),
    ("Sadia Sultana",                   "Assistant Professor", "sadia@cu.ac.bd",             False),
    ("Jewel Dey",                       "Assistant Professor", "jewel@cu.ac.bd",             False),
    ("Tahasin Ahmed Fahim",             "Assistant Professor", "tahasin@cu.ac.bd",           False),
    ("Mohammad Jahed",                  "Assistant Professor", "jahed.eee@cu.ac.bd",         False),
    ("Sangita Rani Basu",               "Assistant Professor", "sangita@cu.ac.bd",           False),
    ("Md. Ali Munna",                   "Assistant Professor", "mdalimunna.eee@cu.ac.bd",    False),
    ("Israt Jahan",                     "Lecturer",            "israt@cu.ac.bd",             False),
]

# who teaches each 5th-semester course (2023–24 batch)
COURSE_TEACHERS = {
    "EEE 510": ["Dr. Md. Murshadul Hoque"],
    "EEE 511": ["Dr. Kazi Tanvir Ahmmed"],
    "EEE 512": ["Dr. Kazi Tanvir Ahmmed", "Dr. Ariful Islam"],
    "EEE 513": ["Sabrina Alam"],
    "EEE 514": ["Sabrina Alam"],
    "EEE 515": ["Dr. Mohammad Shuhrawardy"],
    "EEE 516": ["Sangita Rani Basu", "Dr. Mohammad Shuhrawardy"],
    "CSE 517": ["Sadia Sultana"],
    "CSE 518": ["Sadia Sultana", "Dr. Md. Fazlul Kader"],
    "EEE 519": ["Tahasin Ahmed Fahim"],
}

CONTACT = {
    "address": "Department of Electrical and Electronic Engineering, Faculty of Engineering, "
               "University of Chittagong, Chittagong-4331, Bangladesh",
    "email": "chairman.eee@cu.ac.bd",
    "website": "http://cu.ac.bd/eee",
    "phone": "88-031-2606001-10, 726311-14, 2606015-27 (ext. 4392)",
    "fax": "88-031-2606014, 2606145",
}


# Each teacher's photo and official profile, from the department's faculty page
# on the university website (cu.ac.bd/dept/facultyprofile.php?menumapno=130&secno=21).
# The photos are shown straight from cu.ac.bd; nothing is copied here.
# name: (photo file under CU_PHOTO, profile number "ein" for CU_PROFILE)
CU_PHOTO = "https://cu.ac.bd/assets/image/faculty_staff_users/"
CU_PROFILE = "https://cu.ac.bd/public_profile/index.php?ein="
CU_PAGE = {
    "Dr. Kazi Tanvir Ahmmed":             ("77_PUXXQ2UGQM.jpg", 4825),
    "Dr. Md. Fazlul Kader":               ("74_7MIXYSG5Q5.jpg", 4605),
    "Dr. Jamal Uddin Ahamed":             ("70_QWDQ8I0YES.jpg", 4446),
    "Dr. Hasan Khaled Rouf":              ("68_T3ZVZ6184E.jpg", 4164),
    "Dr. Mohammad Abdul Alim":            ("71_TTMFGSR8ZB.jpg", 4547),
    "Dr. Mohammad Arif Iftakher Mahmood": ("73_AADLW2047D.jpg", 4227),
    "Dr. Md. Murshadul Hoque":            ("72_Y957SIJ2Y2.jpg", 4603),
    "Dr. Md. Shah Alam":                  ("76_EY3M2MQMWE.jpg", 4821),
    "Dr. Mohammad Shuhrawardy":           ("80_NSUI8KQTPJ.jpg", 4930),
    "Dr. Ariful Islam":                   ("78_AA9D5H5S1K.jpg", 4931),
    "S. M. Abu Zahed Chowdhury":          ("79_T258IRIO01.jpg", 5057),
    "Sabrina Alam":                       (None,                5053),   # no photo on the CU page yet
    "Saumitra Kumar Kuri":                ("85_MRWILYI8JT.jpg", 5169),
    "Sabuj Chowdhury":                    ("81_FTUG5UR9ZI.jpg", 5055),
    "Dr. Mohammad Shah Alamgir":          ("84_9X0IQ8DDA9.jpg", 5167),
    "Md. Shariful Islam":                 ("983_KSHTAWC7L0.jpg", 5904),
    "Tauhidul Haque":                     ("982_UDQV2UHWTU.jpg", 5903),
    "Sadia Sultana":                      ("1082_2SEEMNLJPN.jpg", 6126),
    "Jewel Dey":                          ("1087_2ACAOSNDPD.jpg", 6128),
    "Tahasin Ahmed Fahim":                ("1081_5YUJ3687SY.jpg", 6130),
    "Mohammad Jahed":                     ("1080_NMO72VXTOD.jpg", 6127),
    "Sangita Rani Basu":                  ("1088_OXE97FEPSH.jpg", 6125),
    "Md. Ali Munna":                      ("1086_DIQEAZUBGI.jpg", 6124),
}


# Research areas, copied by hand from each teacher's official CU profile ("Areas of
# Interest" tab). Only teachers listed here have areas; for everyone else the
# assistant says it doesn't have them. Do NOT fill this from an automatic page
# reader: the profile pages load their tabs with JavaScript and a reader gets a
# wrong, identical list for everyone (checked 23 Nov 2026).
AREAS = {
    "Dr. Md. Shah Alam": ["Spintronics", "Magnetic Materials", "Quantum Cellular Automata (QCA)",
                          "Photovoltaics/Solar Cell"],
}


def listing():
    out = []
    for n, d, e, leave in FACULTY:
        photo, ein = CU_PAGE.get(n, (None, None))
        out.append({"name": n, "designation": d, "email": e, "on_leave": leave, "chairman": n == CHAIRMAN,
                    "photo": CU_PHOTO + photo if photo else "",
                    "profile": CU_PROFILE + str(ein) if ein else "",
                    "areas": AREAS.get(n, [])})
    return out


def by_email(email):
    email = (email or "").strip().lower()
    for n, d, e, leave in FACULTY:
        if e.lower() == email:
            return n
    return None


def apply_course_teachers(connect):
    """Write the teacher names into the course list, so every page shows them."""
    con = connect()
    for code, names in COURSE_TEACHERS.items():
        con.execute("UPDATE course_meta SET teacher=? WHERE course_id IN "
                    "(SELECT course_id FROM courses WHERE code=? AND semester=5)",
                    (" / ".join(names), code))
    con.commit()
    con.close()
