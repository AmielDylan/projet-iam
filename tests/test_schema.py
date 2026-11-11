"""Schema migrator: SQL files from 010 onward are applied once, at startup."""
from unittest.mock import MagicMock, patch

from app.services.schema import SchemaMigrator, split_statements


class TestSplitStatements:
    def test_plain_statements_and_comments(self):
        sql = """
        -- a comment
        CREATE TABLE a (id INT);
        INSERT INTO a VALUES (1);
        """
        assert split_statements(sql) == ['CREATE TABLE a (id INT)', 'INSERT INTO a VALUES (1)']

    def test_delimiter_blocks_keep_inner_semicolons(self):
        sql = """
        DROP TRIGGER IF EXISTS t;
        DELIMITER ;;
        CREATE TRIGGER t BEFORE UPDATE ON a FOR EACH ROW
        BEGIN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'no';
        END;;
        DELIMITER ;
        SELECT 1;
        """
        statements = split_statements(sql)
        assert statements[0] == 'DROP TRIGGER IF EXISTS t'
        assert statements[1].startswith('CREATE TRIGGER t')
        assert "SET MESSAGE_TEXT = 'no';" in statements[1]
        assert statements[1].rstrip().endswith('END')
        assert statements[2] == 'SELECT 1'


class TestSchemaMigrator:
    def make_dir(self, tmp_path, files):
        for name, body in files.items():
            (tmp_path / name).write_text(body, encoding='utf-8')
        return tmp_path

    def test_applies_only_new_files_from_010_in_order(self, tmp_path):
        directory = self.make_dir(tmp_path, {
            '009_old.sql': 'SELECT 9;',
            '011_b.sql': 'SELECT 11;',
            '010_a.sql': 'SELECT 10;',
            '012_c.sql': 'SELECT 12;',
        })
        cursor = MagicMock()
        cursor.fetchall.return_value = [('011_b.sql',)]
        with patch('app.services.schema.DatabasePool') as db:
            db.get_cursor.return_value.__enter__.return_value = cursor
            applied = SchemaMigrator.apply_pending(directory)

        assert applied == ['010_a.sql', '012_c.sql']
        executed = [str(call.args[0]) for call in cursor.execute.call_args_list]
        assert 'SELECT 10' in executed and 'SELECT 12' in executed
        assert 'SELECT 9' not in executed and 'SELECT 11' not in executed
        assert executed.index('SELECT 10') < executed.index('SELECT 12')
