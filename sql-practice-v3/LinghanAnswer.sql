-- Q21 step 1: look before you filter
SELECT account_id, dept_name, balance
FROM acct_extract_first
ORDER BY account_id DESC
LIMIT 5;
---find that sql result sort to have text first and total > digit. next query 
---filter out the digit 

----Next: steps 3–4 together. Add OR dept_name IS NULL, 
SELECT 'First' AS File, account_id, dept_name, balance
FROM acct_extract_first
WHERE account_id NOT GLOB '[0-9]*'
    OR dept_name IS NULL
UNION ALL
SELECT 'Second' AS File, account_id, dept_name, balance
FROM acct_extract_second
WHERE account_id NOT GLOB '[0-9]*'
   OR dept_name IS NULL;


---//Answer for Q21 "The first export used a 'current' filter, not October, so I don't trust it until the data inside proves which month it is."

----label the file with 'first' AS file, then UNION ALL the same 


----SELECT on acct_extract_second. Expect 4 rows. Step 5 is reading 
---the two filter lines.

---Then Q22. A good stopping point before your 4:00 call is around 2.
