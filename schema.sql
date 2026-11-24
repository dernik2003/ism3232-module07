CREATE TABLE IF NOT EXISTS repairs (
    ticket_id TEXT PRIMARY KEY,
    customer TEXT NOT NULL,
    bike TEXT NOT NULL,
    status TEXT NOT NULL,
    pickup_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS parts (
    name TEXT PRIMARY KEY,
    price REAL NOT NULL,
    stock INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS change_requests (
    number INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id TEXT NOT NULL,
    new_value TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'waiting'
);

INSERT OR IGNORE INTO repairs VALUES
('R200', 'Jordan Lee', 'road bike', 'in repair', '2026-11-20'),
('R201', 'Priya Nair', 'kids bike', 'ready', '2026-11-18'),
('R202', 'Alex Martin', 'mountain bike', 'waiting for parts', '2026-11-28'),
('R203', 'Emma Wilson', 'hybrid bike', 'in repair', '2026-11-29'),
('R204', 'Daniel Scott', 'road bike', 'ready', '2026-11-27');

INSERT OR IGNORE INTO parts VALUES
('inner tube', 8.00, 25),
('brake pads', 15.00, 0),
('bike chain', 22.00, 12),
('pedals', 18.50, 8),
('tire', 35.00, 6);
