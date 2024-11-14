from telegram.ext import ConversationHandler

# Состояния для ConversationHandler
(
    FULL_NAME,              # 1
    BARCODE,               # 2
    BARCODE_AUTH,          # 3
    MENU,                  # 4
    LOGIN,                 # 5
    EDIT_CHOICE,           # 6
    EDIT_NAME,             # 7
    EDIT_BARCODE,          # 8
    EDIT_HIRE_DATE,        # 9
    ADMIN_CODE,            # 10
    ADMIN_MENU,            # 11
    SELECT_USER,           # 12
    SELECT_POSITION,       # 13
    ADD_STORE,             # 14
    STORE_NUMBER,          # 15
    STORE_ADDRESS,         # 16
    SELECT_STORE,          # 17
    SELECT_ADMIN,          # 18
    ASSIGN_STORES,         # 19
    STORES_MENU,           # 20
    DELETE_STORE,          # 21
    SELECT_STORE_EMPLOYEES, # 22
    SELECT_EMPLOYEE,       # 23
    EMPLOYEE_ACTIONS,      # 24
    ADMIN_ACTIONS,         # 25
    REMOVE_ADMIN,          # 26
    EDIT_STORE,           # 27
    USER_MANAGEMENT,       # 28
    REGISTRATION_TYPE,     # 29
    STORE_AUTH,           # 30
    SCHEDULE_MENU,         # 31
    VIEW_SCHEDULE,         # 32
    EDIT_SCHEDULE,         # 33
    CREATE_SCHEDULE,       # 34
    ADD_SUBSTITUTION_STORE, # 35
    ADD_SUBSTITUTION_DATE,  # 36
    ADD_SUBSTITUTION_HOURS,  # 37
    EDIT_SUBSTITUTION,      # 38
    DELETE_SUBSTITUTION,    # 39
    SELECT_SUBSTITUTION_DATE  # 40
) = range(40)