-- OPTIONAL: add an attribute to users. Run only if you want this extra column.
-- Existing rows have NULL in note. The MVP draw.io does not include this column yet.
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS note text;

-- To add another attribute, create a NEW migration file, for example:
-- ALTER TABLE public.users ADD COLUMN employee_number varchar(50);
-- Do not rerun a CREATE TABLE script to change an existing table.
