import pathlib
import attr
from clldutils.misc import slug
from pylexibank import Dataset as BaseDataset
from pylexibank import progressbar as pb
from pylexibank import Language
from pylexibank import FormSpec
import lingpy
from clldutils.text import split_text_with_context, strip_brackets

POSTPROCESSING = [
        ("ayu", "a j u"),
        ("iye", "i j e"),
        ("iyɑ", "i j ɑ"),
        ("ya", "j a"),
        ("y", "j"),
        ("ks", "k s"),
        ("ms", "m s"),
        ("mm", "m m"),
        ("ãũ", "ãu"),
        ("_", "+"),
        ("ãĩ", "ãi")
        ]

@attr.s
class CustomLanguage(Language):
    Location = attr.ib(default=None)
    Remark = attr.ib(default=None)


class Dataset(BaseDataset):
    dir = pathlib.Path(__file__).parent
    id = "liunewari"
    language_class = CustomLanguage
    form_spec = FormSpec(separators="~;,/", missing_data=["∅"], first_form_only=True)

    def cmd_makecldf(self, args):
        # add bib
        args.writer.add_sources()
        args.log.info("added sources")

        # add concept
        concepts = args.writer.add_concepts(
            id_factory=lambda c: c.id.split("-")[-1] + "_" + slug(c.english),
            lookup_factory="Name",
        )

        # correct lookup
        concepts["to smell(perceive odor)[tr.]"] = concepts["to smell (perceive odor) [transitive]"]
        concepts["he or she [3rd sg.]"] = concepts["he or she [third person singular]"]
        concepts["the horn(keratinized skin)"] = concepts["the horn (keratinized skin)"]
        concepts["thou [2nd sg.]"] = concepts["thou [second person singular]"]
        concepts["to burn [intr]"] = concepts["to burn [intransitive]"]
        concepts["the nail(fingernail or claw)"] = concepts["the nail (fingernail or claw)"]
        

        data = self.raw_dir.read_csv("data.tsv", delimiter="\t")

        D = {0: [
            "doculect", "concept", "value", "form", "tokens", "source", "cognate",
            "borrowing", "note"]}
        idx = 1
        for row in data[1:]:
            concept, cog = row[0], row[1]
            bor = row[14]
            for i, doc in zip([2, 5, 8, 11], ["OldNewari", "ClassicalNewari",
                                              "KathmanduNewari", "DolakhaNewari"]):
                val, forms, ref = row[i], row[i+1], row[i+2]
                if ref.strip() and " " in ref and ref.count(" ") == 1:
                    ref, page = ref.strip().split(" ")
                else:
                    page = ""
                for form in split_text_with_context(forms, separators=",/"):
                    if form.strip():
                        D[idx] = [doc, concept, val, form,
                                  lingpy.ipa2tokens(
                                      strip_brackets(form).strip().replace(" ", "_").replace("-", ""),
                                      semi_diacritics="sʃɕʂʑʐʒ"
                                      ), ref+"["+page+"]" if ref.strip() else "", cog, True if
                                  bor.strip() else False, row[-1]]
                        idx += 1
        wl = lingpy.Wordlist(D)
        wl.renumber("cognate", "cogid")


        # add language
        languages = args.writer.add_languages(lookup_factory="Name")
        args.log.info("added languages")

            
        errors = set()
        for idx in wl:
            if wl[idx, "concept"] in concepts:
                tks = " ".join(wl[idx, "tokens"])
                for s, t in POSTPROCESSING:
                    tks = tks.replace(s, t)
                args.writer.add_form_with_segments(
                        Language_ID=wl[idx, "doculect"],
                        Parameter_ID=concepts[wl[idx, "concept"]],
                        Value=wl[idx, "value"],
                        Form=wl[idx, "form"],
                        Segments=tks.split(),
                        Source=wl[idx, "source"],
                        Cognacy=wl[idx, "cognate"],
                        Loan=wl[idx, "borrowing"],
                        Comment=wl[idx, "note"]
                        )
            else:
                errors.add(wl[idx, "concept"])
        for error in errors:
            print(error)
            



