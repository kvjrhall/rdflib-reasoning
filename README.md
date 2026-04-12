# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/kvjrhall/rdflib-reasoning/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                                                            |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------------------------------------------------------------------ | -------: | -------: | ------: | --------: |
| rdflib-reasoning-axioms/src/rdflib\_reasoning/axiom/\_\_init\_\_.py                             |        0 |        0 |    100% |           |
| rdflib-reasoning-axioms/src/rdflib\_reasoning/axiom/common.py                                   |        6 |        0 |    100% |           |
| rdflib-reasoning-axioms/src/rdflib\_reasoning/axiom/structural\_element.py                      |       77 |       27 |     65% |39, 42, 46, 68, 74, 79, 96, 101-115, 119-140, 149, 154 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/\_\_init\_\_.py                            |        6 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/api.py                                     |      158 |        8 |     95% |166, 184, 246-254, 303 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/batch\_dispatcher.py                       |       73 |        2 |     97% |  125, 157 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/derivation.py                              |       34 |        2 |     94% |   66, 103 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/proof.py                                   |       91 |        1 |     99% |        12 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rete/\_\_init\_\_.py                       |        8 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rete/agenda.py                             |       40 |        2 |     95% |    64, 67 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rete/callbacks.py                          |       16 |        6 |     62% |     41-48 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rete/compiler.py                           |       79 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rete/consequents.py                        |       37 |        3 |     92% |     76-78 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rete/facts.py                              |       15 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rete/network.py                            |      221 |        5 |     98% |302-303, 372, 381, 393 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rete/tms.py                                |      102 |        7 |     93% |34, 37, 90, 94, 169, 174, 183 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rete\_store.py                             |       86 |       15 |     83% |85, 92-93, 98, 102, 130, 142, 149, 160, 177, 181, 185, 189, 193, 197 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rules.py                                   |       48 |        4 |     92% |11-12, 24, 32 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rulesets/\_\_init\_\_.py                   |        2 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rulesets/rdfs.py                           |       15 |        0 |    100% |           |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/\_\_init\_\_.py                    |        9 |        0 |    100% |           |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/\_message\_heuristics.py           |       96 |        9 |     91% |67-68, 75, 79-80, 88, 104, 120, 172 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/continuation\_guard\_middleware.py |      256 |       27 |     89% |93, 97, 103, 191-198, 285-289, 300-306, 332-334, 348, 367, 443, 451, 459, 469, 474, 528, 553, 566 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/continuation\_state.py             |       10 |        0 |    100% |           |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/dataset\_middleware.py             |      400 |       70 |     82% |435, 439-440, 467, 479, 524-531, 577-583, 608-609, 619-624, 736-742, 782-783, 787-798, 807, 809, 813-814, 823, 828-838, 857-859, 872, 891, 914, 918, 929, 939-946, 951, 955-957, 1004, 1097-1098, 1113, 1136-1141 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/dataset\_model.py                  |      145 |       17 |     88% |65, 67, 72, 125, 135, 137-138, 142-147, 157, 389, 393, 399-400 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/dataset\_state.py                  |        2 |        0 |    100% |           |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/ministral\_middleware.py           |       17 |        2 |     88% |     50-56 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/namespaces/\_\_init\_\_.py         |        0 |        0 |    100% |           |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/namespaces/spec\_cache.py          |      128 |       19 |     85% |173, 180, 234, 239, 241, 243, 248-249, 281-283, 295-303, 335, 341, 351 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/namespaces/spec\_index.py          |       36 |        3 |     92% |44, 51, 56 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/namespaces/spec\_normalizer.py     |      135 |       20 |     85% |193, 196, 233-238, 250-256, 264, 309, 315, 324-329, 337-342, 357-359 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/namespaces/spec\_whitelist.py      |      100 |        0 |    100% |           |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/rdf\_vocabulary\_middleware.py     |      236 |       31 |     87% |334-340, 351-357, 443-447, 502, 538-542, 605-614, 623, 625, 627-631, 647, 688, 700-702, 760-761 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/shared\_services.py                |       53 |       15 |     72% |26-45, 59, 62-63, 91-92 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/tracing.py                         |       63 |        3 |     95% | 46, 89-90 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/vocabulary\_configuration.py       |       75 |        5 |     93% |20, 22, 25, 53, 119 |
| src/rdflib\_reasoning/\_\_init\_\_.py                                                           |        2 |        0 |    100% |           |
| **TOTAL**                                                                                       | **2877** |  **303** | **89%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/kvjrhall/rdflib-reasoning/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/kvjrhall/rdflib-reasoning/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/kvjrhall/rdflib-reasoning/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/kvjrhall/rdflib-reasoning/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2Fkvjrhall%2Frdflib-reasoning%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/kvjrhall/rdflib-reasoning/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.