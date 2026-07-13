# Central DB Full Ingestion Dependency Graph

`FOUNDATION -> {A0,U0}`

`A0 -> A1 -> A2 -> A3 -> {A4,A5,A6}`

`U0 -> U1 -> {U2,U3,U5}; U0 -> U4; U5 -> U6`

`{A0,A1,A2,A3,A4,A5,A6,U0,U1,U2,U3,U4,U5,U6} -> X1`; `{all accepted lanes} -> X2`

Only one physical writer may run. A-share and US callbacks release independently.
