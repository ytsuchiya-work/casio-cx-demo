WITH x AS (SELECT id.source src, id.record_id rec, profile_id FROM main.${IDR}.identity_xref),
j AS (SELECT x.*, t.person_id FROM x JOIN main.casio_cx._truth_xref t ON t.record_id = x.rec),
p AS (SELECT profile_id, count(DISTINCT person_id) persons, count(*) recs FROM j GROUP BY 1),
q AS (SELECT person_id, count(DISTINCT profile_id) profiles FROM j GROUP BY 1)
SELECT (SELECT count(*) FROM x) records, (SELECT count(DISTINCT profile_id) FROM x) profiles,
       (SELECT count(DISTINCT person_id) FROM j) true_persons,
       (SELECT count(*) FROM p WHERE persons > 1) mixed_profiles,
       (SELECT round(100 * avg(IF(profiles = 1, 1, 0)), 1) FROM q) pct_person_in_one_profile,
       (SELECT collect_set(src) FROM x) sources
