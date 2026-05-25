from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('kyc_sessions', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AnalysisResult',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('overall_score', models.DecimalField(decimal_places=4, max_digits=5)),
                ('verdict', models.CharField(choices=[('genuine', 'Genuine'), ('suspicious', 'Suspicious'), ('fake', 'Fake')], max_length=20)),
                ('face_manipulation_score', models.DecimalField(decimal_places=4, max_digits=5, null=True)),
                ('face_manipulation_confidence', models.DecimalField(decimal_places=4, max_digits=5, null=True)),
                ('lipsync_score', models.DecimalField(decimal_places=4, max_digits=5, null=True)),
                ('lipsync_offset_ms', models.IntegerField(blank=True, null=True)),
                ('rppg_quality', models.DecimalField(decimal_places=4, max_digits=5, null=True)),
                ('rppg_heart_rate', models.DecimalField(decimal_places=2, max_digits=5, null=True)),
                ('av_correlation_score', models.DecimalField(decimal_places=4, max_digits=5, null=True)),
                ('frame_consistency_score', models.DecimalField(decimal_places=4, max_digits=5, null=True)),
                ('faces_detected', models.IntegerField(default=0)),
                ('frames_analyzed', models.IntegerField(default=0)),
                ('processing_time_ms', models.IntegerField(blank=True, null=True)),
                ('model_versions', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('session', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='analysis_result', to='kyc_sessions.kycsession')),
            ],
            options={'db_table': 'analysis_results'},
        ),
        migrations.CreateModel(
            name='FrameScore',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('frame_number', models.IntegerField()),
                ('timestamp_ms', models.IntegerField()),
                ('face_detected', models.BooleanField(default=False)),
                ('face_bbox', models.JSONField(blank=True, null=True)),
                ('face_confidence', models.DecimalField(blank=True, decimal_places=4, max_digits=5, null=True)),
                ('manipulation_score', models.DecimalField(blank=True, decimal_places=4, max_digits=5, null=True)),
                ('is_anomaly', models.BooleanField(default=False)),
                ('heatmap_s3_key', models.CharField(blank=True, max_length=500, null=True)),
                ('result', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='frame_scores', to='analysis.analysisresult')),
            ],
            options={'db_table': 'frame_scores', 'ordering': ['frame_number']},
        ),
        migrations.AddIndex(
            model_name='framescore',
            index=models.Index(fields=['result', 'frame_number'], name='frame_score_result__a1b2c3_idx'),
        ),
    ]
