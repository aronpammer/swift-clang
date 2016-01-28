# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

from ...unit import fixtures
from . import make_args, silent_check_call, silent_call, create_empty_file
import unittest

import os.path
import json


class CompilationDatabaseTest(unittest.TestCase):
    @staticmethod
    def run_intercept(tmpdir, args):
        result = os.path.join(tmpdir, 'cdb.json')
        make = make_args(tmpdir) + args
        silent_check_call(
            ['intercept-build', '--cdb', result] + make)
        return result

    @staticmethod
    def count_entries(filename):
        with open(filename, 'r') as handler:
            content = json.load(handler)
            return len(content)

    def test_successful_build(self):
        with fixtures.TempDir() as tmpdir:
            result = self.run_intercept(tmpdir, ['build_regular'])
            self.assertTrue(os.path.isfile(result))
            self.assertEqual(5, self.count_entries(result))

    def test_successful_build_with_wrapper(self):
        with fixtures.TempDir() as tmpdir:
            result = os.path.join(tmpdir, 'cdb.json')
            make = make_args(tmpdir) + ['build_regular']
            silent_check_call(['intercept-build', '--cdb', result,
                               '--override-compiler'] + make)
            self.assertTrue(os.path.isfile(result))
            self.assertEqual(5, self.count_entries(result))

    @unittest.skipIf(os.getenv('TRAVIS'), 'ubuntu make return -11')
    def test_successful_build_parallel(self):
        with fixtures.TempDir() as tmpdir:
            result = self.run_intercept(tmpdir, ['-j', '4', 'build_regular'])
            self.assertTrue(os.path.isfile(result))
            self.assertEqual(5, self.count_entries(result))

    @unittest.skipIf(os.getenv('TRAVIS'), 'ubuntu env remove clang from path')
    def test_successful_build_on_empty_env(self):
        with fixtures.TempDir() as tmpdir:
            result = os.path.join(tmpdir, 'cdb.json')
            make = make_args(tmpdir) + ['CC=clang', 'build_regular']
            silent_check_call(['intercept-build', '--cdb', result,
                               'env', '-'] + make)
            self.assertTrue(os.path.isfile(result))
            self.assertEqual(5, self.count_entries(result))

    def test_successful_build_all_in_one(self):
        with fixtures.TempDir() as tmpdir:
            result = self.run_intercept(tmpdir, ['build_all_in_one'])
            self.assertTrue(os.path.isfile(result))
            self.assertEqual(5, self.count_entries(result))

    def test_not_successful_build(self):
        with fixtures.TempDir() as tmpdir:
            result = os.path.join(tmpdir, 'cdb.json')
            make = make_args(tmpdir) + ['build_broken']
            silent_call(
                ['intercept-build', '--cdb', result] + make)
            self.assertTrue(os.path.isfile(result))
            self.assertEqual(2, self.count_entries(result))


class ExitCodeTest(unittest.TestCase):
    @staticmethod
    def run_intercept(tmpdir, target):
        result = os.path.join(tmpdir, 'cdb.json')
        make = make_args(tmpdir) + [target]
        return silent_call(
            ['intercept-build', '--cdb', result] + make)

    def test_successful_build(self):
        with fixtures.TempDir() as tmpdir:
            exitcode = self.run_intercept(tmpdir, 'build_clean')
            self.assertFalse(exitcode)

    def test_not_successful_build(self):
        with fixtures.TempDir() as tmpdir:
            exitcode = self.run_intercept(tmpdir, 'build_broken')
            self.assertTrue(exitcode)


class ResumeFeatureTest(unittest.TestCase):
    @staticmethod
    def run_intercept(tmpdir, target, args):
        result = os.path.join(tmpdir, 'cdb.json')
        make = make_args(tmpdir) + [target]
        silent_check_call(
            ['intercept-build', '--cdb', result] + args + make)
        return result

    @staticmethod
    def count_entries(filename):
        with open(filename, 'r') as handler:
            content = json.load(handler)
            return len(content)

    def test_overwrite_existing_cdb(self):
        with fixtures.TempDir() as tmpdir:
            result = self.run_intercept(tmpdir, 'build_clean', [])
            self.assertTrue(os.path.isfile(result))
            result = self.run_intercept(tmpdir, 'build_regular', [])
            self.assertTrue(os.path.isfile(result))
            self.assertEqual(2, self.count_entries(result))

    def test_append_to_existing_cdb(self):
        with fixtures.TempDir() as tmpdir:
            result = self.run_intercept(tmpdir, 'build_clean', [])
            self.assertTrue(os.path.isfile(result))
            result = self.run_intercept(tmpdir, 'build_regular', ['--append'])
            self.assertTrue(os.path.isfile(result))
            self.assertEqual(5, self.count_entries(result))


class ResultFormatingTest(unittest.TestCase):
    @staticmethod
    def run_intercept(tmpdir, command):
        result = os.path.join(tmpdir, 'cdb.json')
        silent_check_call(
            ['intercept-build', '--cdb', result] + command,
            cwd=tmpdir)
        with open(result, 'r') as handler:
            content = json.load(handler)
            return content

    def assert_creates_number_of_entries(self, command, count):
        with fixtures.TempDir() as tmpdir:
            filename = os.path.join(tmpdir, 'test.c')
            create_empty_file(filename)
            command.append(filename)
            cmd = ['sh', '-c', ' '.join(command)]
            cdb = self.run_intercept(tmpdir, cmd)
            self.assertEqual(count, len(cdb))

    def test_filter_preprocessor_only_calls(self):
        self.assert_creates_number_of_entries(['cc', '-c'], 1)
        self.assert_creates_number_of_entries(['cc', '-c', '-E'], 0)
        self.assert_creates_number_of_entries(['cc', '-c', '-M'], 0)
        self.assert_creates_number_of_entries(['cc', '-c', '-MM'], 0)

    def assert_command_creates_entry(self, command, expected):
        with fixtures.TempDir() as tmpdir:
            filename = os.path.join(tmpdir, command[-1])
            create_empty_file(filename)
            cmd = ['sh', '-c', ' '.join(command)]
            cdb = self.run_intercept(tmpdir, cmd)
            self.assertEqual(' '.join(expected), cdb[0]['command'])

    def test_filter_preprocessor_flags(self):
        self.assert_command_creates_entry(
            ['cc', '-c', '-MD', 'test.c'],
            ['cc', '-c', 'test.c'])
        self.assert_command_creates_entry(
            ['cc', '-c', '-MMD', 'test.c'],
            ['cc', '-c', 'test.c'])
        self.assert_command_creates_entry(
            ['cc', '-c', '-MD', '-MF', 'test.d', 'test.c'],
            ['cc', '-c', 'test.c'])

    def test_pass_language_flag(self):
        self.assert_command_creates_entry(
            ['cc', '-c', '-x', 'c', 'test.c'],
            ['cc', '-c', '-x', 'c', 'test.c'])
        self.assert_command_creates_entry(
            ['cc', '-c', 'test.c'],
            ['cc', '-c', 'test.c'])

    def test_pass_arch_flags(self):
        self.assert_command_creates_entry(
            ['clang', '-c', 'test.c'],
            ['cc', '-c', 'test.c'])
        self.assert_command_creates_entry(
            ['clang', '-c', '-arch', 'i386', 'test.c'],
            ['cc', '-c', '-arch', 'i386', 'test.c'])
        self.assert_command_creates_entry(
            ['clang', '-c', '-arch', 'i386', '-arch', 'armv7l', 'test.c'],
            ['cc', '-c', '-arch', 'i386', '-arch', 'armv7l', 'test.c'])