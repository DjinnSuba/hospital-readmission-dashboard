# Generated by Django 4.2.17 on 2025-01-02 10:56

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_alter_account_role'),
    ]

    operations = [
        migrations.AlterField(
            model_name='admission',
            name='patient',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='admissions', to='core.patient'),
        ),
    ]
