#coding: utf-8
import re
from os.path import abspath, dirname, join, basename, splitext
from nltk.tokenize import line_tokenize, word_tokenize
from nsi.metadataextractor.preparator import Preparator
from nsi.metadataextractor.xml_parser import Parser

ROOT = join(abspath(dirname(__file__)), '..')

class TccExtractor(object):

    def __init__(self, doc_dir):
        convertion_style = ""
        parse = Parser(join(ROOT, 'templates', 'tcc.xml'))
        self._template_metadata = parse.xml_template_metadata()
        page = self._template_metadata['page']
        pages = self._template_metadata['pages']
        self._preparator = Preparator(doc_dir)
        self._raw_onepage_doc = self._preparator.raw_text_convertion(page, page, convertion_style)
        self._raw_variouspages_doc = self._preparator.raw_text_convertion(pages[0], pages[1], convertion_style)
        self._linetokenized_onepage_raw_doc = open('%s.txt' %self._preparator.doc_dir).readlines()
        self._clean_variouspages_doc = self._raw_variouspages_doc.replace('\n', ' ')
        self._linetokenized_onepage_doc = line_tokenize(self._raw_onepage_doc)
        self._wordtokenized_onepage_doc = self._preparator.wordtokenized_punctuation_exclusion(self._raw_onepage_doc)
        self.linebreak = "\n"

    def _author_metadata(self):
        self.authors = []
        name_corpus = self._preparator.parse_corpus('names')
        residues = self._template_metadata['author_residue']
        breakers = self._template_metadata['author_breaker']
        for line in self._linetokenized_onepage_doc:
            line_mod = set(word_tokenize(line))
            corpus_common = bool(line_mod.intersection(name_corpus))
            has_residue = bool(line_mod.intersection(residues))
            has_breaker = bool(line_mod.intersection(breakers))
            if corpus_common and not has_residue:
                self.authors.append(line.title())
            elif has_breaker: break
        return self.authors

    def _title_start_point(self):
        last_author_index = 0
        authors = self._author_metadata()

        if authors:
            last_author_index = self._linetokenized_onepage_doc.index(authors[-1].lower())

        return last_author_index + 1

    def _title_metadata(self):
        title_start_point = self._title_start_point()
        title_end_point = 0
        page_lines_len = len(self._linetokenized_onepage_doc)

        breakers = self._template_metadata['title_breaker']

        for title_index in range(title_start_point, page_lines_len):
            if (self._linetokenized_onepage_doc[title_index] in breakers) or title_index == page_lines_len - 1:
                title_end_point = title_index
                break

        return self._linetokenized_onepage_doc[title_start_point:title_end_point]


    def _institution_metadata(self):
        self.institution = u"Instituto Federal de Educação Ciência e Tecnologia "
        institution_validator = set(self._template_metadata['institution_validator'])
        has_institution = bool(institution_validator.intersection(self._wordtokenized_onepage_doc))
        if has_institution:
            institution_corpus = self._preparator.parse_corpus('institution')
            for preposition, institution in institution_corpus:
                institution_mod = set(institution.split())
                if institution_mod.intersection(self._wordtokenized_onepage_doc) == institution_mod:
                    self.institution = self.institution + preposition + institution.title()
                    break
        return self.institution

    def _campus_metadata(self):
        self.campus = ''
        campus_validator = set(self._template_metadata['campus_validator'])
        has_campus = bool(campus_validator.intersection(self._wordtokenized_onepage_doc))

        if has_campus:
            self.campus_corpus = self._preparator.parse_corpus('campus')
            for campus in self.campus_corpus:
                campus_mod = set(campus.split())
                if campus_mod.intersection(self._wordtokenized_onepage_doc) == campus_mod:
                    self.campus = campus.title()
                    break
        return self.campus

    def _abstract_metadata(self):
        regex = re.compile(r'resumo:* (.*?) (palavr(a|as)(.|\s)chav(e|es).|abstract)')
        abstract_match = regex.search(self._clean_variouspages_doc)
        if abstract_match:
            return abstract_match.group(1).strip().capitalize()
        else:
            return ''

    def _grade_metadata(self):
        self.grade = ''
        temp_grade_level = 0
        doc = self._raw_onepage_doc.replace('\n', ' ')
        self.grade_references = {('Graduação', 1):      self._template_metadata['grade_graduation'],
                                 ('Especialização', 2): self._template_metadata['grade_spec'],
                                 ('Mestrado', 3):       self._template_metadata['grade_master_degree'],
                                 ('Doutorado', 4):      self._template_metadata['grade_doctoral'],
                                 ('Pós-Doutorado', 5):  self._template_metadata['grade_postdoctoral']
                                 }
        for grade in self.grade_references.iterkeys():
            grade_type, grade_level = grade
            for grade_name in self.grade_references[grade]:
                if grade_name in doc and grade_level > temp_grade_level:
                    temp_grade_level = grade_level
                    self.grade = grade_type
                    break
        return self.grade

    def all_metadata(self):
        if self._preparator.doc_ext == '.pdf':
            try:
                pdf_embed_metadata = self._preparator.pdf_embed_metadata()
                self._pdf_num_pages = pdf_embed_metadata.numPages
            except:
                print 'Encripted document'
                self._pdf_num_pages = 0
        else:
            self._pdf_num_pages = 0

        metadata = {'author_metadata':      self._author_metadata(),
                    'grade_metadata':       self._grade_metadata(),
                    'title_metadata':       self._title_metadata(),
                    'institution_metadata': self._institution_metadata(),
                    'campus_metadata':      self._campus_metadata(),
                    'abstract_metadata':    self._abstract_metadata(),
                    'number_pages':         self._pdf_num_pages
                    }
        try:
            self._preparator.remove_converted_document()
        except OSError:
            print 'Temporary document already removed..'
        return metadata