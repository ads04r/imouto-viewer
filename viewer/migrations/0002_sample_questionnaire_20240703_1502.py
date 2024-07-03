from django.db import migrations

def add_hads_questionnaire(apps, schema_editor):

	Questionnaire = apps.get_model("viewer", "Questionnaire")
	QuestionnaireQuestion = apps.get_model("viewer", "QuestionnaireQuestion")
	QuestionnaireAnswer = apps.get_model("viewer", "QuestionnaireAnswer")
	if Questionnaire.objects.count() > 0:
		return # Data exists, so we don't need to create any sample data

	hads = Questionnaire(label="HADS (Hospital Anxiety and Depression Scale)", random_order=True, enforce_answers=True, description="A questionnaire commonly used by doctors to determine the levels of anxiety and depression that a person is experiencing.", intro_text="Select the answer closest to how you have been feeling over the last seven days.")
	hads.save()

	q = QuestionnaireQuestion(ordering=1, questionnaire=hads, question="I feel tense or 'wound up'")
	q.save()
	QuestionnaireAnswer(ordering=1, question=q, answer="Most of the time", reading_key="hads-a", reading_value="3").save()
	QuestionnaireAnswer(ordering=2, question=q, answer="A lot of the time", reading_key="hads-a", reading_value="2").save()
	QuestionnaireAnswer(ordering=3, question=q, answer="Occasionally", reading_key="hads-a", reading_value="1").save()
	QuestionnaireAnswer(ordering=4, question=q, answer="Not at all", reading_key="hads-a", reading_value="0").save()

	q = QuestionnaireQuestion(ordering=2, questionnaire=hads, question="I still enjoy the things I used to enjoy")
	q.save()
	QuestionnaireAnswer(ordering=1, question=q, answer="Definitely as much", reading_key="hads-d", reading_value="0").save()
	QuestionnaireAnswer(ordering=2, question=q, answer="Not quite so much", reading_key="hads-d", reading_value="1").save()
	QuestionnaireAnswer(ordering=3, question=q, answer="Only a little", reading_key="hads-d", reading_value="2").save()
	QuestionnaireAnswer(ordering=4, question=q, answer="Hardly at all", reading_key="hads-d", reading_value="3").save()

	q = QuestionnaireQuestion(ordering=3, questionnaire=hads, question="I get a sort of frightened feeling as if something awful is about to happen")
	q.save()
	QuestionnaireAnswer(ordering=1, question=q, answer="Very definitely and quite badly", reading_key="hads-a", reading_value="3").save()
	QuestionnaireAnswer(ordering=2, question=q, answer="Yes, but not too badly", reading_key="hads-a", reading_value="2").save()
	QuestionnaireAnswer(ordering=3, question=q, answer="A little, but it doesn't worry me", reading_key="hads-a", reading_value="1").save()
	QuestionnaireAnswer(ordering=4, question=q, answer="Not at all", reading_key="hads-a", reading_value="0").save()

	q = QuestionnaireQuestion(ordering=4, questionnaire=hads, question="I can laugh and see the funny side of things")
	q.save()
	QuestionnaireAnswer(ordering=1, question=q, answer="As much as I always could", reading_key="hads-d", reading_value="0").save()
	QuestionnaireAnswer(ordering=2, question=q, answer="Not quite so much now", reading_key="hads-d", reading_value="1").save()
	QuestionnaireAnswer(ordering=3, question=q, answer="Definitely not so much now", reading_key="hads-d", reading_value="2").save()
	QuestionnaireAnswer(ordering=4, question=q, answer="Not at all", reading_key="hads-d", reading_value="3").save()

	q = QuestionnaireQuestion(ordering=5, questionnaire=hads, question="Worrying thoughts go through my mind")
	q.save()
	QuestionnaireAnswer(ordering=1, question=q, answer="A great deal of the time", reading_key="hads-a", reading_value="3").save()
	QuestionnaireAnswer(ordering=2, question=q, answer="A lot of the time", reading_key="hads-a", reading_value="2").save()
	QuestionnaireAnswer(ordering=3, question=q, answer="From time to time, but not too often", reading_key="hads-a", reading_value="1").save()
	QuestionnaireAnswer(ordering=4, question=q, answer="Only occasionally", reading_key="hads-a", reading_value="0").save()

	q = QuestionnaireQuestion(ordering=6, questionnaire=hads, question="I feel cheerful")
	q.save()
	QuestionnaireAnswer(ordering=1, question=q, answer="Not at all", reading_key="hads-d", reading_value="3").save()
	QuestionnaireAnswer(ordering=2, question=q, answer="Not often", reading_key="hads-d", reading_value="2").save()
	QuestionnaireAnswer(ordering=3, question=q, answer="Sometimes", reading_key="hads-d", reading_value="1").save()
	QuestionnaireAnswer(ordering=4, question=q, answer="Most of the time", reading_key="hads-d", reading_value="0").save()

	q = QuestionnaireQuestion(ordering=7, questionnaire=hads, question="I can sit at ease and feel relaxed")
	q.save()
	QuestionnaireAnswer(ordering=1, question=q, answer="Definitely", reading_key="hads-a", reading_value="0").save()
	QuestionnaireAnswer(ordering=2, question=q, answer="Usually", reading_key="hads-a", reading_value="1").save()
	QuestionnaireAnswer(ordering=3, question=q, answer="Not often", reading_key="hads-a", reading_value="2").save()
	QuestionnaireAnswer(ordering=4, question=q, answer="Not at all", reading_key="hads-a", reading_value="3").save()

	q = QuestionnaireQuestion(ordering=8, questionnaire=hads, question="I feel as if I am slowed down")
	q.save()
	QuestionnaireAnswer(ordering=1, question=q, answer="Nearly all the time", reading_key="hads-d", reading_value="3").save()
	QuestionnaireAnswer(ordering=2, question=q, answer="Very often", reading_key="hads-d", reading_value="2").save()
	QuestionnaireAnswer(ordering=3, question=q, answer="Sometimes", reading_key="hads-d", reading_value="1").save()
	QuestionnaireAnswer(ordering=4, question=q, answer="Not at all", reading_key="hads-d", reading_value="0").save()

	q = QuestionnaireQuestion(ordering=9, questionnaire=hads, question="I get a sort of frightened feeling like 'butterflies' in the stomach")
	q.save()
	QuestionnaireAnswer(ordering=1, question=q, answer="Not at all", reading_key="hads-a", reading_value="0").save()
	QuestionnaireAnswer(ordering=2, question=q, answer="Occasionally", reading_key="hads-a", reading_value="1").save()
	QuestionnaireAnswer(ordering=3, question=q, answer="Quite often", reading_key="hads-a", reading_value="2").save()
	QuestionnaireAnswer(ordering=4, question=q, answer="Very often", reading_key="hads-a", reading_value="3").save()

	q = QuestionnaireQuestion(ordering=10, questionnaire=hads, question="I have lost interest in my appearance")
	q.save()
	QuestionnaireAnswer(ordering=1, question=q, answer="Definitely", reading_key="hads-d", reading_value="3").save()
	QuestionnaireAnswer(ordering=2, question=q, answer="I don't take as much care as I should", reading_key="hads-d", reading_value="2").save()
	QuestionnaireAnswer(ordering=3, question=q, answer="I may not take quite as much care", reading_key="hads-d", reading_value="1").save()
	QuestionnaireAnswer(ordering=4, question=q, answer="I take just as much care as ever", reading_key="hads-d", reading_value="0").save()

	q = QuestionnaireQuestion(ordering=11, questionnaire=hads, question="I feel restless as I have to be on the move")
	q.save()
	QuestionnaireAnswer(ordering=1, question=q, answer="Very much indeed", reading_key="hads-a", reading_value="3").save()
	QuestionnaireAnswer(ordering=2, question=q, answer="Quite a lot", reading_key="hads-a", reading_value="2").save()
	QuestionnaireAnswer(ordering=3, question=q, answer="Not very much", reading_key="hads-a", reading_value="1").save()
	QuestionnaireAnswer(ordering=4, question=q, answer="Not at all", reading_key="hads-a", reading_value="0").save()

	q = QuestionnaireQuestion(ordering=12, questionnaire=hads, question="I look forward with enjoyment to things")
	q.save()
	QuestionnaireAnswer(ordering=1, question=q, answer="As much as I ever did", reading_key="hads-d", reading_value="0").save()
	QuestionnaireAnswer(ordering=2, question=q, answer="Rather less than I used to", reading_key="hads-d", reading_value="1").save()
	QuestionnaireAnswer(ordering=3, question=q, answer="Definitely less than I used to", reading_key="hads-d", reading_value="2").save()
	QuestionnaireAnswer(ordering=4, question=q, answer="Hardly at all", reading_key="hads-d", reading_value="3").save()

	q = QuestionnaireQuestion(ordering=13, questionnaire=hads, question="I get sudden feelings of panic")
	q.save()
	QuestionnaireAnswer(ordering=1, question=q, answer="Very often indeed", reading_key="hads-a", reading_value="3").save()
	QuestionnaireAnswer(ordering=2, question=q, answer="Quite often", reading_key="hads-a", reading_value="2").save()
	QuestionnaireAnswer(ordering=3, question=q, answer="Not very often", reading_key="hads-a", reading_value="1").save()
	QuestionnaireAnswer(ordering=4, question=q, answer="Not at all", reading_key="hads-a", reading_value="0").save()

	q = QuestionnaireQuestion(ordering=14, questionnaire=hads, question="I can enjoy a good book or TV program")
	q.save()
	QuestionnaireAnswer(ordering=1, question=q, answer="Often", reading_key="hads-d", reading_value="0").save()
	QuestionnaireAnswer(ordering=2, question=q, answer="Sometimes", reading_key="hads-d", reading_value="1").save()
	QuestionnaireAnswer(ordering=3, question=q, answer="Not often", reading_key="hads-d", reading_value="2").save()
	QuestionnaireAnswer(ordering=4, question=q, answer="Very seldom", reading_key="hads-d", reading_value="3").save()

class Migration(migrations.Migration):

    dependencies = [ ('viewer', '0001_initial') ]
    operations = [ migrations.RunPython(add_hads_questionnaire) ]
