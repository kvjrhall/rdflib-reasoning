# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/kvjrhall/rdflib-reasoning/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                                                            |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------------------------------------------------------------------ | -------: | -------: | ------: | --------: |
| rdflib-reasoning-axioms/src/rdflib\_reasoning/axiom/\_\_init\_\_.py                             |        0 |        0 |    100% |           |
| rdflib-reasoning-axioms/src/rdflib\_reasoning/axiom/common.py                                   |        6 |        0 |    100% |           |
| rdflib-reasoning-axioms/src/rdflib\_reasoning/axiom/structural\_element.py                      |       77 |       27 |     65% |39, 42, 46, 68, 74, 79, 96, 101-115, 119-140, 149, 154 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/\_\_init\_\_.py                            |        9 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/api.py                                     |      282 |       13 |     95% |282, 300, 399-409, 487, 558-560 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/batch\_dispatcher.py                       |       73 |        2 |     97% |  133, 165 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/builtins.py                                |       36 |        5 |     86% |15, 25, 35, 45, 56 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/derivation.py                              |      109 |       18 |     83% |25-34, 38, 114-116, 130-131, 134, 159, 222, 267, 292 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/proof.py                                   |      101 |        1 |     99% |        12 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/proof\_notebook.py                         |       24 |        2 |     92% |    48, 55 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/proof\_rendering.py                        |      183 |       26 |     86% |83, 125, 147-149, 156, 175, 182, 200, 209-222, 234-240, 252-253 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rete/\_\_init\_\_.py                       |        8 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rete/agenda.py                             |       40 |        2 |     95% |    64, 67 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rete/callbacks.py                          |       16 |        6 |     62% |     42-49 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rete/compiler.py                           |       83 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rete/consequents.py                        |       50 |        5 |     90% |   100-104 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rete/facts.py                              |       15 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rete/network.py                            |      229 |        2 |     99% |  138, 394 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rete/tms.py                                |      298 |       14 |     95% |51, 60, 86, 178, 285, 290, 302, 341, 357, 363, 371, 401, 490, 521 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rete\_store.py                             |      131 |       18 |     86% |158, 175, 182-183, 188, 192, 232-233, 257, 269, 276, 287, 304, 308, 312, 316, 320, 324 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rules.py                                   |       54 |        4 |     93% |11-12, 24, 32 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rulesets/\_\_init\_\_.py                   |        5 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rulesets/owl2\_rl\_contradictions.py       |       14 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rulesets/rdf\_axioms.py                    |       13 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rulesets/rdfs.py                           |       37 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rulesets/rdfs\_axioms.py                   |       17 |        0 |    100% |           |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/\_\_init\_\_.py                    |        9 |        0 |    100% |           |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/\_message\_heuristics.py           |       96 |        9 |     91% |67-68, 75, 79-80, 104, 120, 169, 172 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/continuation\_guard\_middleware.py |      472 |       57 |     88% |131, 135, 141, 181, 185-186, 188, 262, 267, 269-273, 279, 282, 285, 373-380, 467-471, 482-488, 511, 514-516, 528-541, 602, 680, 731, 750, 826, 834, 842, 852, 857, 898-908, 918, 960, 1049, 1075 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/continuation\_state.py             |       13 |        0 |    100% |           |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/dataset\_middleware.py             |      400 |       77 |     81% |435, 439-440, 467, 479, 524-531, 577-583, 601-605, 608-609, 619-624, 736-742, 782-783, 787-798, 807, 809, 813-814, 823, 828-838, 857-859, 872, 891, 899, 914, 918, 929, 939-946, 950-951, 955-957, 1004, 1076-1080, 1097-1098, 1113, 1136-1141 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/dataset\_model.py                  |      145 |       18 |     88% |65, 67, 72, 125, 135, 137-138, 142-147, 157, 363, 389, 393, 399-400 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/dataset\_state.py                  |        2 |        0 |    100% |           |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/ministral\_middleware.py           |       17 |        2 |     88% |     50-56 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/namespaces/\_\_init\_\_.py         |        0 |        0 |    100% |           |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/namespaces/\_bundled.py            |       76 |        1 |     99% |        40 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/namespaces/common.py               |        6 |        0 |    100% |           |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/namespaces/spec\_cache.py          |      132 |        7 |     95% |105, 110, 112, 114, 119-120, 277 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/namespaces/spec\_index.py          |       38 |        6 |     84% |35, 38, 41, 48, 55, 60 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/namespaces/spec\_normalizer.py     |      135 |       19 |     86% |196, 199, 236-241, 253-259, 312, 318, 327-332, 340-345, 360-362 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/namespaces/spec\_whitelist.py      |      100 |        0 |    100% |           |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/rdf\_vocabulary\_middleware.py     |      313 |       31 |     90% |498-507, 635-639, 712, 726, 728, 769-773, 841, 843, 845-849, 865, 917, 921, 947, 956, 1062, 1068, 1079-1080 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/shared\_services.py                |       53 |       15 |     72% |26-45, 59, 62-63, 91-92 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/tracing.py                         |      305 |       36 |     88% |75, 85, 87-91, 98, 104-119, 125, 138, 144, 147, 427, 439, 528, 554, 560-561, 577, 621, 652-653 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/tracing\_notebook.py               |      155 |       21 |     86% |53, 69, 112, 142-145, 158, 160, 174, 229-230, 236, 240, 268, 287, 311-312, 315-316, 320 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/vocabulary/\_\_init\_\_.py         |        0 |        0 |    100% |           |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/vocabulary/search\_index.py        |      165 |        2 |     99% |   283-284 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/vocabulary/search\_model.py        |       15 |        0 |    100% |           |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/vocabulary\_configuration.py       |       79 |        4 |     95% |26, 28, 31, 76 |
| **TOTAL**                                                                                       | **4636** |  **450** | **90%** |           |


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