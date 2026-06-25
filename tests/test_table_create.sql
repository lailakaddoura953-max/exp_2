CREATE TABLE container_demo (
    [CONT_ID] INTEGER,
    [TIME_STAMP] TEXT NOT NULL, -- SQLite uses TEXT for ISO8601 time strings
    [CONT_ACTION] TEXT NOT NULL CHECK ([CONT_ACTION] IN ('PICKED', 'GROUNDED')),
    [CONT_NAME] TEXT NOT NULL,  -- Numeric sequences stored as TEXT to preserve leading zeros
    [LocalTimeStamp] TEXT NOT NULL,
    [orgheight] REAL,
    [orglength] REAL,
    [orgweight] REAL,
    [measuredheight] REAL,
    [measuredlength] REAL,
    [measuredweight] REAL,
    [Tier] INTEGER CHECK ([Tier] IS NULL OR ([Tier] >= 0 AND [Tier] <= 3)),
    [IsoCode] INTEGER,
    [LocationX] REAL,
    [LocationY] REAL,
    [LocationHeading] REAL,
    [CHE] TEXT NOT NULL, -- Format example: SC001 - SC135
    
    -- Composite primary key definition
    PRIMARY KEY ([CONT_ID], [CHE])
);
