from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0012_transaction_site_address_transaction_site_contact_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='party',
            name='advance_balance',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=12),
        ),
    ]
