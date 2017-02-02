##
# Copyright (c) 2016-present MagicStack Inc.
# All rights reserved.
#
# See LICENSE for details.
##


import os.path
import unittest

from edgedb.client import exceptions as exc
from edgedb.server import _testbase as tb


class TestExpressions(tb.QueryTestCase):
    SCHEMA = os.path.join(os.path.dirname(__file__), 'schemas',
                          'queries.eschema')

    SETUP = """
    """

    TEARDOWN = """
    """

    async def test_edgeql_expr_emptyset_01(self):
        await self.assert_query_result(r"""
            SELECT <int>EMPTY;
            SELECT <str>EMPTY;
            SELECT EMPTY + 1;
            SELECT 1 + EMPTY;
        """, [
            [None],
            [None],
            [None],
            [None],
        ])

        with self.assertRaisesRegex(exc.EdgeQLError,
                                    r'could not determine expression type'):

            await self.con.execute("""
                SELECT EMPTY;
            """)

    async def test_edgeql_expr_op01(self):
        await self.assert_query_result(r"""
            SELECT 40 + 2;
            SELECT 40 - 2;
            SELECT 40 * 2;
            SELECT 40 / 2;
            SELECT 40 % 2;
        """, [
            [42],
            [38],
            [80],
            [20],
            [0],
        ])

    async def test_edgeql_expr_op02(self):
        await self.assert_query_result(r"""
            SELECT 40 ^ 2;
            SELECT 121 ^ 0.5;
            SELECT 2 ^ 3 ^ 2;
        """, [
            [1600],
            [11],
            [2 ** 3 ** 2],
        ])

    async def test_edgeql_expr_op03(self):
        await self.assert_query_result(r"""
            SELECT 40 < 2;
            SELECT 40 > 2;
            SELECT 40 <= 2;
            SELECT 40 >= 2;
            SELECT 40 = 2;
            SELECT 40 != 2;
        """, [
            [False],
            [True],
            [False],
            [True],
            [False],
            [True],
        ])

    async def test_edgeql_expr_op04(self):
        await self.assert_query_result(r"""
            SELECT -1 + 2 * 3 - 5 - 6.0 / 2;
            SELECT
                -1 + 2 * 3 - 5 - 6.0 / 2 > 0
                OR 25 % 4 = 3 AND 42 IN (12, 42, 14);
            SELECT (-1 + 2) * 3 - (5 - 6.0) / 2;
            SELECT
                ((-1 + 2) * 3 - (5 - 6.0) / 2 > 0 OR 25 % 4 = 3)
                AND 42 IN (12, 42, 14);
            SELECT 1 * 0.2;
            SELECT 0.2 * 1;
            SELECT -0.2 * 1;
            SELECT 0.2 + 1;
            SELECT 1 + 0.2;
            SELECT -0.2 - 1;
            SELECT -1 - 0.2;
            SELECT -1 / 0.2;
            SELECT 0.2 / -1;
        """, [
            [-3],
            [False],
            [3.5],
            [True],
            [0.2],
            [0.2],
            [-0.2],
            [1.2],
            [1.2],
            [-1.2],
            [-1.2],
            [-5],
            [-0.2],
        ])

    async def test_edgeql_expr_op05(self):
        await self.assert_query_result(r"""
            SELECT 'foo' + 'bar';
        """, [
            ['foobar'],
        ])

    async def test_edgeql_expr_op06(self):
        await self.assert_query_result(r"""
            SELECT EMPTY = EMPTY;
            SELECT EMPTY = 42;
            SELECT EMPTY = 'EMPTY';
        """, [
            [None],
            [None],
            [None],
        ])

    async def test_edgeql_expr_op07(self):
        await self.assert_query_result(r"""
            SELECT EXISTS EMPTY;
            SELECT NOT EXISTS EMPTY;
        """, [
            [False],
            [True],
        ])

    async def test_edgeql_expr_op08(self):
        with self.assertRaisesRegex(
                exc.EdgeQLError,
                r'unary operator `-` is not defined .* std::str'):

            await self.con.execute("""
                SELECT -'aaa';
            """)

    async def test_edgeql_expr_op09(self):
        with self.assertRaisesRegex(
                exc.EdgeQLError,
                r'unary operator `NOT` is not defined .* std::str'):

            await self.con.execute("""
                SELECT NOT 'aaa';
            """)

    async def test_edgeql_expr_op10(self):
        for query in ['SELECT -EMPTY;', 'SELECT +EMPTY;', 'SELECT NOT EMPTY;']:
            with self.assertRaisesRegex(
                    exc.EdgeQLError,
                    r'unary operator `.+` is not defined for empty set'):

                await self.con.execute(query)

    async def test_edgeql_expr_op11(self):
        # Test non-trivial folding
        await self.assert_query_result(r"""
            SELECT 1 + (1 + len([1, 2])) + 1;
            SELECT 2 * (2 * len([1, 2])) * 2;
        """, [
            [5],
            [16],
        ])

    async def test_edgeql_expr_paths_01(self):
        cases = [
            "Issue.owner.name",
            "`Issue`.`owner`.`name`",
            "Issue.(test::owner).name",
            "`Issue`.(`test`::`owner`).`name`",
            "Issue.(owner).(name)",
            "test::`Issue`.(`test`::`owner`).`name`",
            "Issue.((owner)).(((test::name)))",
        ]

        for case in cases:
            await self.con.execute('''
                WITH MODULE test
                SELECT
                    Issue {
                        test::number
                    }
                WHERE
                    %s = 'Elvis';
            ''' % (case,))

    async def test_edgeql_expr_polymorphic_01(self):
        await self.con.execute(r"""
            WITH MODULE test
            SELECT Text {
                Issue.number,
                (Issue).related_to,
                (Issue).((`priority`)),
                test::Comment.owner: {
                    name
                }
            };
        """)

        await self.con.execute(r"""
            WITH MODULE test
            SELECT Owned {
                Named.name
            };
        """)

    async def test_edgeql_expr_cast01(self):
        await self.assert_query_result(r"""
            SELECT <std::str>123;
            SELECT <std::int>"123";
            SELECT <std::str>123 + 'qw';
            SELECT <std::int>"123" + 9000;
            SELECT <std::int>"123" * 100;
            SELECT <std::str>(123 * 2);
            SELECT <int>true;
            SELECT <int>false;
        """, [
            ['123'],
            [123],
            ['123qw'],
            [9123],
            [12300],
            ['246'],
            [1],
            [0],
        ])

    async def test_edgeql_expr_cast02(self):
        # testing precedence of casting vs. multiplication
        #
        with self.assertRaisesRegex(
                exc.EdgeQLError,
                r'operator `\*` is not defined .* std::str and std::int'):

            await self.con.execute("""
                SELECT <std::str>123 * 2;
            """)

    async def test_edgeql_expr_cast03(self):
        await self.assert_query_result(r"""
            SELECT <std::str><std::int><std::float>'123.45' + 'foo';
        """, [
            ['123foo'],
        ])

    async def test_edgeql_expr_cast04(self):
        await self.assert_query_result(r"""
            SELECT <str><int><float>'123.45' + 'foo';
        """, [
            ['123foo'],
        ])

    async def test_edgeql_expr_cast05(self):
        await self.assert_query_result(r"""
            SELECT <array<int>>['123', '11'];
        """, [
            [[123, 11]],
        ])

    async def test_edgeql_expr_cast06(self):
        await self.assert_query_result(r"""
            SELECT <array<bool>>['t', 'tr', 'tru', 'true'];
            SELECT <array<bool>>['T', 'TR', 'TRU', 'TRUE'];
            SELECT <array<bool>>['True', 'TrUe', '1'];
            SELECT <array<bool>>['y', 'ye', 'yes'];
            SELECT <array<bool>>['Y', 'YE', 'YES'];
            SELECT <array<bool>>['Yes', 'yEs', 'YeS'];
        """, [
            [[True, True, True, True]],
            [[True, True, True, True]],
            [[True, True, True]],
            [[True, True, True]],
            [[True, True, True]],
            [[True, True, True]],
        ])

    async def test_edgeql_expr_cast07(self):
        await self.assert_query_result(r"""
            SELECT <array<bool>>['f', 'fa', 'fal', 'fals', 'false'];
            SELECT <array<bool>>['F', 'FA', 'FAL', 'FALS', 'FALSE'];
            SELECT <array<bool>>['False', 'FaLSe', '0'];
            SELECT <array<bool>>['n', 'no'];
            SELECT <array<bool>>['N', 'NO'];
            SELECT <array<bool>>['No', 'nO'];
        """, [
            [[False, False, False, False, False]],
            [[False, False, False, False, False]],
            [[False, False, False]],
            [[False, False]],
            [[False, False]],
            [[False, False]],
        ])

    async def test_edgeql_expr_type01(self):
        await self.assert_query_result(r"""
            SELECT 'foo'.__class__.name;
        """, [
            ['std::str'],
        ])

    async def test_edgeql_expr_type02(self):
        await self.assert_query_result(r"""
            SELECT (1.0 + 2).__class__.name;
        """, [
            ['std::float'],
        ])

    async def test_edgeql_expr_array01(self):
        await self.assert_query_result("""
            SELECT [1];
            SELECT [1, 2, 3, 4, 5];
            SELECT [1, 2, 3, 4, 5][2];
            SELECT [1, 2, 3, 4, 5][-2];

            SELECT [1, 2, 3, 4, 5][2:4];
            SELECT [1, 2, 3, 4, 5][2:];
            SELECT [1, 2, 3, 4, 5][:2];

            SELECT [1, 2, 3, 4, 5][2:-1];
            SELECT [1, 2, 3, 4, 5][-2:];
            SELECT [1, 2, 3, 4, 5][:-2];

            SELECT [1, 2][10] ?? 42;

            SELECT <array<int>>[];
        """, [
            [[1]],
            [[1, 2, 3, 4, 5]],
            [3],
            [4],

            [[3, 4]],
            [[3, 4, 5]],
            [[1, 2]],

            [[3, 4]],
            [[4, 5]],
            [[1, 2, 3]],

            [42],

            [[]],
        ])

    async def test_edgeql_expr_array02(self):
        with self.assertRaisesRegex(
                exc.EdgeQLError, r'could not determine array type'):

            await self.con.execute("""
                SELECT [1, '1'];
            """)

    async def test_edgeql_expr_array03(self):
        with self.assertRaisesRegex(
                exc.EdgeQLError, r'cannot index array by.*str'):

            await self.con.execute("""
                SELECT [1, 2]['1'];
            """)

    async def test_edgeql_expr_array04(self):
        with self.assertRaisesRegex(
                exc.EdgeQLError,
                r'could not determine type of empty collection'):

            await self.con.execute("""
                SELECT [];
            """)

    async def test_edgeql_expr_map01(self):
        await self.assert_query_result(r"""
            SELECT ['fo' + 'o' -> 42];
            SELECT <map<str,int>>['foo' -> '42'];
            SELECT <map<int,int>>['+1' -> '42'];

            SELECT <map<str,float>>['foo' -> '1.1'];
            SELECT <map<str,float>>['foo' -> '1.0'];
            SELECT <map<float,int>>['+1.5' -> '42'];

            SELECT <map<float,bool>>['+1.5' -> 42];

            SELECT ['foo' -> '42', 'bar' -> 'something'];
            SELECT [lower('FOO') -> '42', 'bar' -> 'something']['foo'];

            SELECT ['foo' -> '42', 'bar' -> 'something'][lower('FO') + 'o'];
            SELECT '+/-' + ['foo' -> '42', 'bar' -> 'something']['foo'];
            SELECT ['foo' -> 42]['foo'] + 1;

            SELECT ['a' -> <datetime>'2017-10-10']['a'] + <timedelta>'1 day';
            SELECT [100 -> 42][100];
            SELECT ['1' -> '2']['spam'] ?? 'ham';

            SELECT [ [[1],[2],[3]] -> 42] [[[1],[2],[3]]];
            SELECT [ [[1] -> 1] -> 42 ] [[[1] -> 1]];
            SELECT [[10+1 ->1] -> 100, [2 ->2] -> 200]
                    [<map<int,int>>['1'+'1' ->'1']];

            SELECT ['aaa' -> [ [['a'->1]], [['b'->2]], [['c'->3]] ] ];

            SELECT <map<int, int>>[];
        """, [
            [{'foo': 42}],
            [{'foo': 42}],
            [{'1': 42}],

            [{'foo': 1.1}],
            [{'foo': 1.0}],
            [{'1.5': 42}],

            [{'1.5': True}],

            [{'foo': '42', 'bar': 'something'}],
            ['42'],

            ['42'],
            ['+/-42'],
            [43],

            ['2017-10-11T00:00:00+00:00'],
            [42],
            ['ham'],

            [42],
            [42],
            [100],

            [{'aaa': [[{'a': 1}], [{'b': 2}], [{'c': 3}]]}],

            [{}]
        ])

    async def test_edgeql_expr_map02(self):
        with self.assertRaisesRegex(
                exc.EdgeQLError, r'could not determine map values type'):

            await self.con.execute(r'''
                SELECT ['a' -> 'b', '1' -> 1];
            ''')

        with self.assertRaisesRegex(
                exc.EdgeQLError,
                r'binary operator `\+` is not defined.*str.*int'):

            await self.con.execute(r'''
                SELECT ['a' -> '1']['a'] + 1;
            ''')

    async def test_edgeql_expr_map03(self):
        await self.con.execute('''
            CREATE FUNCTION test::take(std::map<std::str, std::int>, std::str)
                RETURNING std::int
                FROM EdgeQL $$
                    SELECT $1[$2] + 100
                $$;

            CREATE FUNCTION test::make(std::int)
                RETURNING std::map<std::str, std::int>
                FROM EdgeQL $$
                    SELECT ['aaa' -> $1]
                $$;
        ''')

        await self.assert_query_result(r"""
            SELECT test::take(['foo' -> 42], 'foo') + 1;
            SELECT test::make(1000)['aaa'] + 8000;
        """, [
            [143],
            [9000],
        ])

    async def test_edgeql_expr_map04(self):
        await self.assert_query_result(r"""
            SELECT <map<str, datetime>>['foo' -> '2020-10-10'];
            SELECT (<map<int,int>>['+1' -> '+42'])[1];  # '+1'::bigint = 1
            SELECT (<map<datetime, datetime>>['2020-10-10' -> '2010-01-01'])
                   [<datetime>'2020-10-10'];
            SELECT (<map<int,int>>[true -> '+42'])[1];
            SELECT (<map<bool,int>>(<map<int,str>>[true -> 142]))[true];
        """, [
            [{'foo': '2020-10-10T00:00:00+00:00'}],
            [42],
            ['2010-01-01T00:00:00+00:00'],
            [42],
            [142],
        ])

        with self.assertRaisesRegex(
                exc.EdgeQLError, r'cannot index map.*by.*str.*int.*expected'):

            await self.con.execute(r'''
                SELECT [1 -> 1]['1'];
            ''')

    async def test_edgeql_expr_map05(self):
        await self.assert_query_result(r"""
            SELECT [1 -> [ [[1]], [[-2]], [[3]] ] ]   [1];
            SELECT [1 -> [ [[true]], [[false]], [[true]] ] ]   [1];
            SELECT [1 -> [ [[1.1]], [[-2.2]], [[3.3]] ] ]   [1];
            SELECT [1 -> [ [['aa']], [['bb']], [['cc']] ] ]   [1];
            SELECT [1 -> [ [['aa'->1]], [['bb'->2]], [['cc'->3]] ] ]   [1];
            SELECT [1 -> ['a'->[1,2], 'b'->[1,3]]] [1];
            SELECT [1 -> ['a'->[['x'->10]], 'b'->[['y'->20]]]] [1];
            SELECT [1 -> ['a'->[['x'->10]],'b'->[['y'->20]]]] [1]['a'][0]['x'];
        """, [
            [[[[1]], [[-2]], [[3]]]],
            [[[[True]], [[False]], [[True]]]],
            [[[[1.1]], [[-2.2]], [[3.3]]]],
            [[[['aa']], [['bb']], [['cc']]]],
            [[[{'aa': 1}], [{'bb': 2}], [{'cc': 3}]]],
            [{'a': [1, 2], 'b': [1, 3]}],
            [{'a': [{'x': 10}], 'b': [{'y': 20}]}],
            [10],
        ])

    @unittest.expectedFailure
    async def test_edgeql_expr_map06(self):
        await self.assert_query_result(r"""
            SELECT [1 -> [ [[1]], [[-2]], [[3]] ] ]   [1][0];
            SELECT [1 -> [ [[1]], [[-2]], [[3]] ] ]   [1][0][0];
            SELECT [1 -> [ [[1]], [[-2]], [[3]] ] ]   [1][0][0][0];
        """, [
            [[[1]]],
            [[1]],
            [1],
        ])

    async def test_edgeql_expr_struct01(self):
        with self.assertRaisesRegex(
                exc.EdgeQLError,
                r'operator `\+` is not defined .* struct<.*> and std::int'):

            await self.con.execute(r'''
                SELECT {spam := 1, ham := 2} + 1;
            ''')

    async def test_edgeql_expr_coalesce01(self):
        await self.assert_query_result(r"""
            SELECT EMPTY ?? 4 ?? 5;
            SELECT EMPTY ?? 'foo' ?? 'bar';
            SELECT 4 ?? EMPTY ?? 5;

            SELECT 'foo' ?? EMPTY ?? 'bar';
            SELECT EMPTY ?? 'bar' = 'bar';

            SELECT 4^EMPTY ?? 2;
            SELECT 4+EMPTY ?? 2;
            SELECT 4*EMPTY ?? 2;

            SELECT -<int>EMPTY ?? 2;
            SELECT -<int>EMPTY ?? -2 + 1;

            SELECT <int>(EMPTY ?? EMPTY);
            SELECT <int>(EMPTY ?? EMPTY ?? EMPTY);
        """, [
            [4],
            ['foo'],
            [4],

            ['foo'],
            [True],

            [2],  # ^ binds more tightly
            [6],
            [8],

            [2],
            [-1],

            [None],
            [None],
        ])

    async def test_edgeql_expr_string01(self):
        await self.assert_query_result("""
            SELECT 'qwerty';
            SELECT 'qwerty'[2];
            SELECT 'qwerty'[-2];

            SELECT 'qwerty'[2:4];
            SELECT 'qwerty'[2:];
            SELECT 'qwerty'[:2];

            SELECT 'qwerty'[2:-1];
            SELECT 'qwerty'[-2:];
            SELECT 'qwerty'[:-2];
        """, [
            ['qwerty'],
            ['e'],
            ['t'],

            ['er'],
            ['erty'],
            ['qw'],

            ['ert'],
            ['ty'],
            ['qwer'],
        ])

    async def test_edgeql_expr_string02(self):
        with self.assertRaisesRegex(
                exc.EdgeQLError, r'cannot index string by.*str'):

            await self.con.execute("""
                SELECT '123'['1'];
            """)

    async def test_edgeql_expr_tuple01(self):
        await self.assert_query_result(r"""
            SELECT (1, 'foo');
        """, [
            [[1, 'foo']],
        ])

    async def test_edgeql_expr_tuple02(self):
        await self.assert_query_result(r"""
            SELECT (1, 'foo') = (1, 'foo');
            SELECT (1, 'foo') = (2, 'foo');
            SELECT (1, 'foo') != (1, 'foo');
            SELECT (1, 'foo') != (2, 'foo');
        """, [
            [True],
            [False],
            [False],
            [True],
        ])

    async def test_edgeql_expr_tuple03(self):
        with self.assertRaisesRegex(
                exc._base.UnknownEdgeDBError, r'operator does not exist'):
            await self.con.execute(r"""
                SELECT (1, 2) = [1, 2];
            """)

    async def test_edgeql_expr_tuple04(self):
        with self.assertRaisesRegex(
                exc._base.UnknownEdgeDBError, r'operator does not exist'):
            await self.con.execute(r"""
                SELECT (1, 'foo') = ('1', 'foo');
            """)

    async def test_edgeql_expr_tuple05(self):
        await self.assert_query_result(r"""
            SELECT array_agg((1, 'foo'));
        """, [
            [[[1, 'foo']]],
        ])

    async def test_edgeql_expr_cannot_assign_dunder_class(self):
        with self.assertRaisesRegex(
                exc.EdgeQLError, r'cannot assign to __class__'):
            await self.con.execute(r"""
                SELECT test::Text {
                    std::__class__ := 42
                };
            """)

    async def test_edgeql_expr_if_else_01(self):
        await self.assert_query_result(r"""
            SELECT 'yes' IF 1=1 ELSE 'no';
            SELECT 'yes' IF 1=0 ELSE 'no';
            SELECT 's1' IF 1=0 ELSE 's2' IF 2=2 ELSE 's3';
        """, [
            ['yes'],
            ['no'],
            ['s2'],
        ])

    async def test_edgeql_expr_select(self):
        await self.assert_query_result(r"""
            SELECT 2 * ((SELECT 1) UNION (SELECT 2));

            SELECT (SELECT 2) * (1 UNION 2);

            SELECT 2 * (1 UNION 2 EXCEPT 1);

            WITH
                a := (SELECT 1 UNION 2 EXCEPT 1)
            SELECT (SELECT 2) * a;
        """, [
            [2, 4],
            [2, 4],
            [4],
            [4],
        ])

    async def test_edgeql_expr_cardinality01(self):
        with self.assertRaisesRegex(
                exc.EdgeQLError,
                r'possibly more than one element returned by an expression '
                r'where only singletons are allowed',
                position=44):

            await self.query('''\
                WITH MODULE test
                SELECT Issue.name ORDER BY Issue.watchers.name;
            ''')

    async def test_edgeql_expr_cardinality02(self):
        with self.assertRaisesRegex(
                exc.EdgeQLError,
                r'possibly more than one element returned by an expression '
                r'where only singletons are allowed',
                position=30):

            await self.query('''\
                WITH MODULE test
                SELECT Issue LIMIT User.name;
            ''')

    async def test_edgeql_expr_cardinality03(self):
        with self.assertRaisesRegex(
                exc.EdgeQLError,
                r'possibly more than one element returned by an expression '
                r'where only singletons are allowed',
                position=30):

            await self.query('''\
                WITH MODULE test
                SELECT Issue OFFSET User.name;
            ''')

    async def test_edgeql_expr_type_filter_01(self):
        with self.assertRaisesRegex(
                exc.EdgeQLError,
                r'invalid type filter operand: std::int is not a concept',
                position=7):

            await self.query('''\
                SELECT 10[IS std::Object];
            ''')

    async def test_edgeql_expr_type_filter_02(self):
        with self.assertRaisesRegex(
                exc.EdgeQLError,
                r'invalid type filter operand: std::str is not a concept',
                position=17):

            await self.query('''\
                SELECT Object[IS str];
            ''')

    async def test_edgeql_expr_type_filter_03(self):
        with self.assertRaisesRegex(
                exc.EdgeQLError,
                r'invalid type filter operand: std::uuid is not a concept',
                position=20):

            await self.query('''\
                SELECT Object.id[IS uuid];
            ''')
