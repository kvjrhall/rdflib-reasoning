# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/kvjrhall/rdflib-reasoning/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                                                            |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------------------------------------------------------------------ | -------: | -------: | ------: | --------: |
| rdflib-reasoning-axioms/src/rdflib\_reasoning/axiom/\_\_init\_\_.py                             |        2 |        0 |    100% |           |
| rdflib-reasoning-axioms/src/rdflib\_reasoning/axiom/axiomatize.py                               |      325 |       40 |     88% |132, 139, 148, 156, 172, 180, 203, 211, 221, 248, 252, 269, 279, 306, 316, 344, 348, 363, 373, 440, 463-464, 479, 496, 513-514, 526, 536, 546, 554, 573, 596, 610, 625, 668, 685, 711, 731, 735, 739 |
| rdflib-reasoning-axioms/src/rdflib\_reasoning/axiom/class\_axiom.py                             |       27 |        0 |    100% |           |
| rdflib-reasoning-axioms/src/rdflib\_reasoning/axiom/common.py                                   |        8 |        0 |    100% |           |
| rdflib-reasoning-axioms/src/rdflib\_reasoning/axiom/datatype.py                                 |      177 |        1 |     99% |       553 |
| rdflib-reasoning-axioms/src/rdflib\_reasoning/axiom/n3\_terms.py                                |       81 |        1 |     99% |        64 |
| rdflib-reasoning-axioms/src/rdflib\_reasoning/axiom/structural\_element.py                      |      144 |       12 |     92% |112, 131-138, 162, 168, 342 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/\_\_init\_\_.py                            |        9 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/api.py                                     |       34 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/batch\_dispatcher.py                       |       73 |        2 |     97% |  146, 178 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/builtins.py                                |       96 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/derivation.py                              |      122 |        7 |     94% |97, 101, 113, 204, 268, 314, 339 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/errors.py                                  |        5 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/proof.py                                   |      101 |        1 |     99% |        14 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/proof\_notebook.py                         |       24 |        2 |     92% |    50, 57 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/proof\_rendering.py                        |      183 |       26 |     86% |87, 130, 152-154, 161, 180, 187, 205, 214-227, 239-245, 257-258 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rete/\_\_init\_\_.py                       |        7 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rete/agenda.py                             |       40 |        2 |     95% |    71, 75 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rete/compiler.py                           |       83 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rete/consequents.py                        |       50 |        5 |     90% |   101-105 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rete/facts.py                              |       15 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rete/network.py                            |      229 |        2 |     99% |  141, 401 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rete/tms.py                                |      298 |       14 |     95% |54, 63, 89, 184, 297, 303, 318, 359, 376, 382, 390, 422, 511, 542 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rete\_engine.py                            |      227 |       13 |     94% |171, 189, 287-297, 375, 446-448 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rete\_errors.py                            |       48 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rete\_factory.py                           |       18 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rete\_store.py                             |      132 |       11 |     92% |164, 182, 190-191, 202, 245-246, 271, 305, 344, 349 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rules.py                                   |       38 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rulesets/\_\_init\_\_.py                   |        5 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rulesets/owl2\_rl\_contradictions.py       |       14 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rulesets/rdf\_axioms.py                    |       13 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rulesets/rdfs.py                           |       37 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rulesets/rdfs\_axioms.py                   |       17 |        0 |    100% |           |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/\_\_init\_\_.py                    |       10 |        0 |    100% |           |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/\_message\_heuristics.py           |       96 |        9 |     91% |67-68, 75, 79-80, 104, 120, 168, 171 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/common.py                          |       24 |        1 |     96% |        74 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/continuation\_guard\_middleware.py |      472 |       57 |     88% |133, 137, 143, 183, 187-188, 190, 264, 269, 271-275, 281, 284, 287, 375-382, 469-473, 484-490, 513, 516-518, 530-543, 604, 682, 733, 752, 828, 836, 844, 854, 859, 900-910, 920, 962, 1051, 1077 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/continuation\_state.py             |       13 |        0 |    100% |           |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/dataset\_middleware.py             |      409 |       71 |     83% |59-61, 464, 476, 521-528, 574-580, 598-602, 605-606, 616-621, 733-739, 778-779, 783-792, 801, 803, 807-808, 817, 822-832, 851-853, 866, 885, 893, 908, 912, 923, 933-935, 939-940, 1022, 1026, 1028, 1086, 1088, 1090, 1135-1139, 1156-1157, 1171, 1194-1198 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/dataset\_model.py                  |       69 |       10 |     86% |26-31, 90, 116, 121, 128-129 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/dataset\_state.py                  |        2 |        0 |    100% |           |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/ministral\_middleware.py           |       17 |        2 |     88% |     54-60 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/namespaces/\_\_init\_\_.py         |        0 |        0 |    100% |           |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/namespaces/\_bundled.py            |       76 |        1 |     99% |        40 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/namespaces/common.py               |        6 |        0 |    100% |           |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/namespaces/spec\_cache.py          |      161 |       10 |     94% |124, 179-181, 237, 239, 241, 246-247, 330 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/namespaces/spec\_index.py          |       38 |        6 |     84% |43, 47, 51, 58, 65, 70 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/namespaces/spec\_normalizer.py     |      135 |       19 |     86% |199, 202, 239-244, 256-262, 315, 321, 330-335, 343-348, 363-365 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/namespaces/spec\_whitelist.py      |      100 |        0 |    100% |           |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/rdf\_vocabulary\_middleware.py     |      318 |       31 |     90% |516-525, 653-657, 732, 747, 749, 791-795, 863, 865, 867-871, 887, 939, 943, 969, 978, 1084, 1090, 1107-1108 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/shared\_services.py                |       62 |        0 |    100% |           |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/tracing.py                         |      305 |       36 |     88% |81, 91, 93-97, 104, 110-125, 131, 144, 150, 153, 441, 453, 542, 568, 574-575, 591, 634, 664-665 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/tracing\_notebook.py               |      155 |       21 |     86% |56, 72, 115, 145-148, 161, 163, 177, 232-233, 239, 243, 272, 291, 316-317, 321-322, 326 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/vocabulary/\_\_init\_\_.py         |        0 |        0 |    100% |           |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/vocabulary/search\_index.py        |      165 |        2 |     99% |   296-297 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/vocabulary/search\_model.py        |       15 |        0 |    100% |           |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/vocabulary\_configuration.py       |       90 |        5 |     94% |19, 31, 33, 36, 82 |
| **TOTAL**                                                                                       | **5420** |  **420** | **92%** |           |


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