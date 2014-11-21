BEGIN;
    CREATE TABLE emails
    ( id                                serial                      PRIMARY KEY
    , address                           text                        NOT NULL
    , verified                          boolean                     DEFAULT NULL
    , nonce                             text
    , ctime                             timestamp with time zone    NOT NULL DEFAULT CURRENT_TIMESTAMP
    , mtime                             timestamp with time zone
    , participant                       text                        NOT NULL REFERENCES participants
    , UNIQUE (address, verified) -- One verified email address per person.
     );

    -- The participants table currently has an `email` attribute of type email_address_with confirmation
    -- This should be deleted in the future, once the emails are migrated.
    -- The column we're going to replace it with is named `email_address`. This is only for **verified** emails.
    -- All unverified email stuff happens in the emails table and won't touch this attribute.

    ALTER TABLE participants ADD COLUMN email_address text;
END;
