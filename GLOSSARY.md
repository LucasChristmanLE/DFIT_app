# DFIT interpretation

Terms used when interpreting a single diagnostic fracture injection test by the compliance method.

## Language

**Shut-in point**:
The first sample after pumping stops, as picked on the injection step. All shut-in-relative times are measured from it.
_Avoid_: Shut-in time (when meaning the sample), end of injection

**Apparent ISIP**:
Bottomhole pressure at the shut-in point. Read either from the early pressure-decline tangent extrapolated back to the shut-in point (used when water hammer obscures the first samples), or directly as the pressure at the shut-in point when there is no water hammer.
_Avoid_: ISIP (unqualified), instantaneous shut-in pressure

**Effective ISIP**:
The pressure-vs-G straight line extrapolated to G = 0. Distinct from the apparent ISIP; the difference is near-wellbore complexity.
_Avoid_: ISIP (unqualified)

**Shmin method**:
The closure interpretation a Shmin value comes from: compliance, tangent, variable, Liberty, stiffness, or rapid. Net pressure and closure time are per method; pore pressure is not, since each test has one pore pressure.
_Avoid_: Stress method, interpretation (when meaning the method)

### Test identity

**API / UWI**:
The well's regulatory identifier, logged in the `api` column. A US well has a 10-digit API number (`0512345678`, state prefix first). An Alberta well has no API; it has a Dominion Land Survey UWI, stored in AER ST37 `Well_UWI` form (`00/14-22-065-16W5/0`). The two are told apart by form: all digits is an API, a `W` meridian is a UWI.
_Avoid_: API (when the well is in Alberta), well ID

**Job date**:
The date the DFIT was pumped. One per test.
_Avoid_: Test date, review date (that is when the test was interpreted)

**Operator at test**:
The company that operated the well when the DFIT was pumped, as Liberty recorded it.
_Avoid_: Operator (unqualified), original operator
