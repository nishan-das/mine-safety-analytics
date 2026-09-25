-- ================================================================
--  MINE SAFETY ANALYTICS  -  VERSION 1  -  PURE SQL
-- ================================================================
--  Run all of them at once:
--       python run_sql.py queries/v1_queries.sql
--  Or copy any single query into:
--       python run_sql.py "SELECT ..."
--
--  Q1-Q3   things you already know (SELECT / WHERE / ORDER BY)
--  Q4-Q7   NEW: COUNT and GROUP BY
--  Q8-Q11  NEW: JOIN
--  Q12-Q14 the three findings that make this a safety project
-- ================================================================


-- Q1  What locations exist at this mine?
SELECT location_id, location_name, location_type, zone
FROM locations
ORDER BY zone, location_name;


-- Q2  Show me every fatal or serious injury
SELECT incident_date, shift_id, incident_type, cause_category, days_lost
FROM incidents
WHERE incident_type = 'Fatal' OR incident_type = 'Serious Bodily Injury'
ORDER BY incident_date;


-- Q3  The ten incidents that cost us the most working days
SELECT incident_date, incident_type, cause_category, days_lost, description
FROM incidents
WHERE days_lost > 0
ORDER BY days_lost DESC
LIMIT 10;


-- Q4  How many incidents in total?
SELECT COUNT(*) AS total_incidents
FROM incidents;


-- Q5  How many of each type? (the safety triangle)
SELECT incident_type,
       COUNT(*) AS number_of_incidents
FROM incidents
GROUP BY incident_type
ORDER BY number_of_incidents DESC;


-- Q6  Which hazard category causes the most incidents?
SELECT cause_category,
       COUNT(*)        AS incident_count,
       SUM(days_lost)  AS total_days_lost
FROM incidents
GROUP BY cause_category
ORDER BY incident_count DESC;


-- Q7  Are incidents spread evenly across the three shifts?
SELECT shift_id,
       COUNT(*) AS incident_count
FROM incidents
GROUP BY shift_id
ORDER BY shift_id;


-- Q8  JOIN: put the location NAME next to each incident
--     (the incidents table only stores location_id, a number)
SELECT i.incident_date,
       i.incident_type,
       l.location_name,
       l.zone
FROM incidents AS i
JOIN locations AS l ON i.location_id = l.location_id
WHERE i.days_lost > 0
ORDER BY i.incident_date;


-- Q9  JOIN + GROUP BY: incident count per location
SELECT l.location_name,
       l.zone,
       COUNT(*) AS incident_count
FROM incidents AS i
JOIN locations AS l ON i.location_id = l.location_id
GROUP BY l.location_name, l.zone
ORDER BY incident_count DESC;


-- Q10  Underground vs Surface
SELECT l.zone,
       COUNT(*)       AS incident_count,
       SUM(i.days_lost) AS days_lost
FROM incidents AS i
JOIN locations AS l ON i.location_id = l.location_id
GROUP BY l.zone;


-- Q11  Three-table JOIN: which designations get hurt, and where?
SELECT e.designation,
       l.location_name,
       COUNT(*) AS incident_count
FROM incidents AS i
JOIN employees AS e ON i.emp_id      = e.emp_id
JOIN locations AS l ON i.location_id = l.location_id
WHERE i.days_lost > 0
GROUP BY e.designation, l.location_name
ORDER BY incident_count DESC;


-- Q12  FINDING 1 - counting accidents hides the real story
--      Contractors vs departmental workers, by raw count only.
--      Look at how CLOSE these two numbers are.
SELECT e.employment_type,
       COUNT(*) AS lost_time_injuries
FROM incidents AS i
JOIN employees AS e ON i.emp_id = e.emp_id
WHERE i.incident_type IN ('Reportable Injury',
                          'Serious Bodily Injury',
                          'Fatal')
GROUP BY e.employment_type;


-- Q13  FINDING 2 - the busiest location is not the most dangerous
--      Compare the order of these two columns carefully.
SELECT l.location_name,
       COUNT(*)         AS incident_count,
       SUM(i.days_lost) AS days_lost
FROM incidents AS i
JOIN locations AS l ON i.location_id = l.location_id
GROUP BY l.location_name
ORDER BY days_lost DESC;


-- Q14  FINDING 3 - who has stopped reporting near misses?
--      A location with severe injuries but almost no near-miss
--      reports does not have fewer hazards. It has a reporting gap.
SELECT l.location_name,
       SUM(CASE WHEN i.incident_type = 'Near Miss' THEN 1 ELSE 0 END) AS near_misses,
       SUM(CASE WHEN i.days_lost > 0 THEN 1 ELSE 0 END)               AS lost_time_injuries,
       SUM(i.days_lost)                                               AS days_lost
FROM incidents AS i
JOIN locations AS l ON i.location_id = l.location_id
GROUP BY l.location_name
ORDER BY days_lost DESC;
