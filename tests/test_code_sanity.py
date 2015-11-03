from subprocess import PIPE, Popen

from django.test import TestCase


class CodeSanityTests(TestCase):

    def test_pylint_check(self):
        """
        Use flake8 for testing code quality
        """
        result = Popen('flake8', stdin=PIPE, stdout=PIPE, stderr=PIPE)
        output, err = result.communicate()
        self.assertTrue(result.returncode == 0, 'Flake8 Log not empty\n' + str(output))

    def test_isort_check(self):
        """
        Use isort enforce structured imports.
        """
        result = Popen(
            ['isort', '-c', '-df', '-rc', '.'],
            stdin=PIPE, stdout=PIPE, stderr=PIPE
        )
        output, err = result.communicate()
        self.assertTrue(result.returncode == 0, 'Isort Log not empty\n' + str(output))
