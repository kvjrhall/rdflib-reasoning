# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/kvjrhall/rdflib-reasoning/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                                                            |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------------------------------------------------------------------ | -------: | -------: | ------: | --------: |
| rdflib-reasoning-axioms/src/rdflib\_reasoning/axiom/\_\_init\_\_.py                             |        2 |        0 |    100% |           |
| rdflib-reasoning-axioms/src/rdflib\_reasoning/axiom/axiomatize.py                               |      325 |       40 |     88% |132, 139, 148, 156, 172, 180, 203, 211, 221, 248, 252, 269, 279, 306, 316, 344, 348, 363, 373, 440, 463-464, 479, 496, 513-514, 526, 536, 546, 554, 573, 596, 610, 625, 668, 685, 711, 731, 735, 739 |
| rdflib-reasoning-axioms/src/rdflib\_reasoning/axiom/class\_axiom.py                             |       27 |        0 |    100% |           |
| rdflib-reasoning-axioms/src/rdflib\_reasoning/axiom/common.py                                   |        8 |        0 |    100% |           |
| rdflib-reasoning-axioms/src/rdflib\_reasoning/axiom/datatype.py                                 |      177 |        1 |     99% |       545 |
| rdflib-reasoning-axioms/src/rdflib\_reasoning/axiom/n3\_terms.py                                |       81 |        1 |     99% |        64 |
| rdflib-reasoning-axioms/src/rdflib\_reasoning/axiom/structural\_element.py                      |      144 |       12 |     92% |108, 127-134, 158, 164, 328 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/\_\_init\_\_.py                            |        9 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/api.py                                     |       34 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/batch\_dispatcher.py                       |       73 |        2 |     97% |  133, 165 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/builtins.py                                |       98 |        2 |     98% |  103, 111 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/derivation.py                              |      123 |        7 |     94% |88, 91, 102, 183, 246, 291, 316 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/errors.py                                  |        5 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/proof.py                                   |      101 |        1 |     99% |        12 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/proof\_notebook.py                         |       24 |        2 |     92% |    48, 55 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/proof\_rendering.py                        |      183 |       26 |     86% |83, 125, 147-149, 156, 175, 182, 200, 209-222, 234-240, 252-253 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rete/\_\_init\_\_.py                       |        7 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rete/agenda.py                             |       40 |        2 |     95% |    63, 66 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rete/compiler.py                           |       83 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rete/consequents.py                        |       50 |        5 |     90% |    98-102 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rete/facts.py                              |       15 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rete/network.py                            |      229 |        2 |     99% |  135, 390 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rete/tms.py                                |      298 |       14 |     95% |49, 58, 84, 174, 280, 285, 297, 336, 352, 358, 366, 396, 485, 516 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rete\_engine.py                            |      227 |       13 |     94% |166, 184, 282-292, 370, 441-443 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rete\_errors.py                            |       48 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rete\_factory.py                           |       18 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rete\_store.py                             |      132 |       18 |     86% |159, 176, 183-184, 189, 193, 233-234, 258, 270, 277, 288, 305, 309, 313, 317, 321, 325 |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rules.py                                   |       38 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rulesets/\_\_init\_\_.py                   |        5 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rulesets/owl2\_rl\_contradictions.py       |       14 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rulesets/rdf\_axioms.py                    |       13 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rulesets/rdfs.py                           |       37 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflib\_reasoning/engine/rulesets/rdfs\_axioms.py                   |       17 |        0 |    100% |           |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/\_\_init\_\_.py                    |       10 |        0 |    100% |           |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/\_message\_heuristics.py           |       96 |        9 |     91% |67-68, 75, 79-80, 104, 120, 168, 171 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/continuation\_guard\_middleware.py |      472 |       57 |     88% |131, 135, 141, 181, 185-186, 188, 262, 267, 269-273, 279, 282, 285, 373-380, 467-471, 482-488, 511, 514-516, 528-541, 602, 680, 731, 750, 826, 834, 842, 852, 857, 898-908, 918, 960, 1049, 1075 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/continuation\_state.py             |       13 |        0 |    100% |           |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/dataset\_middleware.py             |      400 |       77 |     81% |434, 438-439, 466, 478, 523-530, 576-582, 600-604, 607-608, 618-623, 735-741, 781-782, 786-797, 806, 808, 812-813, 822, 827-837, 856-858, 871, 890, 898, 913, 917, 928, 938-945, 949-950, 954-956, 1003, 1075-1079, 1096-1097, 1112, 1135-1140 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/dataset\_model.py                  |       67 |       10 |     85% |26-31, 88, 113, 117, 123-124 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/dataset\_state.py                  |        2 |        0 |    100% |           |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/ministral\_middleware.py           |       17 |        2 |     88% |     50-56 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/namespaces/\_\_init\_\_.py         |        0 |        0 |    100% |           |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/namespaces/\_bundled.py            |       76 |        1 |     99% |        40 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/namespaces/common.py               |        6 |        0 |    100% |           |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/namespaces/spec\_cache.py          |      161 |       10 |     94% |114, 167-169, 224, 226, 228, 233-234, 317 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/namespaces/spec\_index.py          |       38 |        6 |     84% |35, 38, 41, 48, 55, 60 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/namespaces/spec\_normalizer.py     |      135 |       19 |     86% |196, 199, 236-241, 253-259, 312, 318, 327-332, 340-345, 360-362 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/namespaces/spec\_whitelist.py      |      100 |        0 |    100% |           |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/rdf\_vocabulary\_middleware.py     |      318 |       31 |     90% |500-509, 637-641, 714, 728, 730, 771-775, 843, 845, 847-851, 867, 919, 923, 949, 958, 1064, 1070, 1081-1082 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/shared\_services.py                |       53 |       15 |     72% |26-45, 59, 62-63, 91-92 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/tracing.py                         |      305 |       36 |     88% |75, 85, 87-91, 98, 104-119, 125, 138, 144, 147, 427, 439, 528, 554, 560-561, 577, 620, 650-651 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/tracing\_notebook.py               |      155 |       21 |     86% |53, 69, 112, 142-145, 158, 160, 174, 229-230, 236, 240, 268, 287, 311-312, 315-316, 320 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/vocabulary/\_\_init\_\_.py         |        0 |        0 |    100% |           |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/vocabulary/search\_index.py        |      165 |        2 |     99% |   283-284 |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/vocabulary/search\_model.py        |       15 |        0 |    100% |           |
| rdflib-reasoning-middleware/src/rdflib\_reasoning/middleware/vocabulary\_configuration.py       |       90 |        5 |     94% |17, 29, 31, 34, 79 |
| **TOTAL**                                                                                       | **5379** |  **449** | **92%** |           |


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