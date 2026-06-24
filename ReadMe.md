# Future Updates:

- Add Multiple Bank Accounts for Single user, so user can track, spend, and save acc. to bank accounts.
- Create an Excel/CSV at the end of the month that contain all the important data about the user's expenses and store it to database.

# App name/logo:

- "**Creduce**": Master Your Money, Grow Your Future.
  Creduce comes from the Latin Credo (to trust) and Accrue (to grow). We believe that financial freedom starts with a system you can trust. By tracking every expense, you aren't just managing money—you are allowing your wealth to accrue naturally through discipline.

---

-- accounts
-- Belongs to a user. Tracks running balance automatically.

---

CREATE TABLE IF NOT EXISTS accounts (
id INT NOT NULL AUTO_INCREMENT,
user_id INT NOT NULL,
name VARCHAR(100) NOT NULL,
type ENUM('bank','wallet','cash','credit_card') NOT NULL DEFAULT 'bank',
initial_balance DECIMAL(15,2) NOT NULL DEFAULT 0.00,
current_balance DECIMAL(15,2) NOT NULL DEFAULT 0.00,
icon VARCHAR(50) NULL,
color VARCHAR(10) NULL,
created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    CONSTRAINT fk_accounts_user FOREIGN KEY (user_id)
        REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE,

    INDEX idx_accounts_user_id (user_id)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

---

-- categories
-- User-defined top-level categories (e.g. Food, Bills).

---

CREATE TABLE IF NOT EXISTS categories (
id INT NOT NULL AUTO_INCREMENT,
user_id INT NOT NULL,
name VARCHAR(100) NOT NULL,
icon VARCHAR(50) NULL,
color VARCHAR(10) NULL,
created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    CONSTRAINT fk_categories_user FOREIGN KEY (user_id)
        REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE,

    UNIQUE INDEX uq_categories_user_name (user_id, name),
    INDEX idx_categories_user_id (user_id)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

---

-- subcategories
-- One level of nesting under a category (e.g. Food → Pizza).

---

CREATE TABLE IF NOT EXISTS subcategories (
id INT NOT NULL AUTO_INCREMENT,
category_id INT NOT NULL,
name VARCHAR(100) NOT NULL,
created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    CONSTRAINT fk_subcategories_category FOREIGN KEY (category_id)
        REFERENCES categories(id) ON DELETE CASCADE ON UPDATE CASCADE,

    UNIQUE INDEX uq_subcategories_cat_name (category_id, name),
    INDEX idx_subcategories_category_id (category_id)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

---

-- transactions
-- Core ledger table. Every income / expense is recorded here.
-- Transfers are recorded in the transfers table and excluded from
-- category / analytics queries.

---

CREATE TABLE IF NOT EXISTS transactions (
id INT NOT NULL AUTO_INCREMENT,
user_id INT NOT NULL,
account_id INT NOT NULL,
category_id INT NULL,
subcategory_id INT NULL,
type ENUM('income','expense','transfer') NOT NULL,
amount DECIMAL(15,2) NOT NULL,
payment_method ENUM('cash','upi','debit_card','credit_card','net_banking') NOT NULL DEFAULT 'cash',
notes TEXT NULL,
transaction_date DATE NOT NULL,
created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    CONSTRAINT fk_txn_user     FOREIGN KEY (user_id)        REFERENCES users(id)         ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_txn_account  FOREIGN KEY (account_id)     REFERENCES accounts(id)      ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_txn_category FOREIGN KEY (category_id)    REFERENCES categories(id)    ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_txn_subcat   FOREIGN KEY (subcategory_id) REFERENCES subcategories(id) ON DELETE SET NULL ON UPDATE CASCADE,

    INDEX idx_txn_user_id          (user_id),
    INDEX idx_txn_account_id       (account_id),
    INDEX idx_txn_transaction_date (transaction_date),
    INDEX idx_txn_type             (type),
    INDEX idx_txn_user_date        (user_id, transaction_date),
    INDEX idx_txn_user_account     (user_id, account_id)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

---

-- transfers
-- Moves money atomically between two accounts belonging to the
-- same user. Excluded from all analytics queries.

---

CREATE TABLE IF NOT EXISTS transfers (
id INT NOT NULL AUTO_INCREMENT,
user_id INT NOT NULL,
from_account_id INT NOT NULL,
to_account_id INT NOT NULL,
amount DECIMAL(15,2) NOT NULL,
notes TEXT NULL,
transfer_date DATE NOT NULL,
created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    CONSTRAINT fk_transfer_user    FOREIGN KEY (user_id)         REFERENCES users(id)    ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_transfer_from    FOREIGN KEY (from_account_id) REFERENCES accounts(id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_transfer_to      FOREIGN KEY (to_account_id)   REFERENCES accounts(id) ON DELETE CASCADE ON UPDATE CASCADE,

    CONSTRAINT chk_transfer_accounts CHECK (from_account_id <> to_account_id),

    INDEX idx_transfers_user_id       (user_id),
    INDEX idx_transfers_from_account  (from_account_id),
    INDEX idx_transfers_to_account    (to_account_id),
    INDEX idx_transfers_date          (transfer_date)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
