# Lokalise Integration Setup Guide

This guide will help you set up Lokalise integration with your Libriya project.

## Step 1: Create Lokalise Account and Project

1. Go to [app.lokalise.com](https://app.lokalise.com) and create an account
2. Create a new project for Libriya
3. Choose "Gettext (.po)" as the file format
4. Set English as the base language
5. Add Polish (and any other languages you want) as target languages

## Step 2: Upload Initial Translation Files

You can upload your existing translation files to Lokalise:

1. In your Lokalise project, go to "Upload"
2. Upload the following files:
   - `messages.pot` (template file from root directory)
   - `translations/en/LC_MESSAGES/messages.po` (English)
   - `translations/pl/LC_MESSAGES/messages.po` (Polish)
3. Ensure the files are mapped to the correct languages

**Note:** The `messages.pot` file is typically generated in the root directory by pybabel.

## Step 3: Get Your Lokalise Credentials

1. **API Token:**
   - Go to your profile → API Tokens
   - Click "Create API token"
   - Give it a name (e.g., "GitHub Actions")
   - Select "Read" and "Write" permissions
   - Copy the token

2. **Project ID:**
   - Go to your Lokalise project
   - The Project ID is in the URL: `app.lokalise.com/project/<PROJECT_ID>`
   - Or find it in Project Settings → General

## Step 4: Add GitHub Secrets

1. Go to your GitHub repository (Settings page)
2. Navigate to Settings → Secrets and variables → Actions
3. Click "New repository secret" and add:
   - Name: `LOKALISE_API_TOKEN`
   - Value: Your API token from Step 3
4. Click "New repository secret" again and add:
   - Name: `LOKALISE_PROJECT_ID`
   - Value: Your Project ID from Step 3

## Step 5: Test the Integration

### Test Push Workflow (GitHub → Lokalise)

**Option 1: Manual Trigger (Recommended for first-time setup)**
1. Go to GitHub Actions tab
2. Click on "Push translations to Lokalise" workflow
3. Click "Run workflow" button
4. Select the `main` branch
5. The workflow will run and upload your translation files to Lokalise
6. Check your Lokalise project to see if the files were uploaded

**Option 2: Automatic Trigger**
1. Make a small change to any translation file (e.g., add a comment to `translations/pl/LC_MESSAGES/messages.po` or `messages.pot`)
2. Commit and push to the `main` branch
3. Go to Actions tab in GitHub and watch the "Push translations to Lokalise" workflow run
4. Check your Lokalise project to see if the files were uploaded

**Note:** If the workflow was added in the initial commit of your repository, you need to use Option 1 (manual trigger) or make a new change to trigger it, as workflows cannot run for the commit that creates them.

### Test Pull Workflow (Lokalise → GitHub)
1. Make a change in Lokalise (edit a translation)
2. Go to GitHub Actions tab
3. Click on "Pull translations from Lokalise" workflow
4. Click "Run workflow" button
5. The workflow will create a pull request with updated translations

## Workflow Details

### Push Workflow (`.github/workflows/push-to-lokalise.yml`)
- **Triggers:** 
  - Automatically when `.po` or `.pot` files in `translations/` or root directory are changed on `main` branch
  - Manual trigger (workflow_dispatch) - can be run on-demand from GitHub Actions tab
- **Action:** Uploads translation template (.pot) and translation files (.po) to Lokalise
- **Purpose:** Keep Lokalise synchronized with your source code

### Pull Workflow (`.github/workflows/pull-from-lokalise.yml`)
- **Triggers:** 
  - Manual trigger (workflow_dispatch)
  - Scheduled: Weekly on Monday at midnight UTC
- **Action:** Downloads translations from Lokalise and creates a PR
- **Purpose:** Bring translated content back to your repository

## Working with Translations

### Extract New Strings
When you add new translatable strings to your code:
```bash
pybabel extract -F babel.cfg -o messages.pot .
pybabel update -i messages.pot -d translations
```

### Compile Translations Locally
```bash
python compile_translations.py
# or
pybabel compile -d translations
```

### Workflow
1. Add new translatable strings in your Flask app (using `gettext()` or `_()`)
2. Extract strings: `pybabel extract -F babel.cfg -o messages.pot .`
3. Update translations: `pybabel update -i messages.pot -d translations`
4. Commit and push to `main` → Automatically syncs to Lokalise
5. Translators work in Lokalise web interface
6. Run "Pull translations from Lokalise" workflow → Creates PR with translations
7. Review and merge the PR
8. Compile translations: `python compile_translations.py`

## Troubleshooting

### Workflow Fails with Authentication Error
- Check that `LOKALISE_API_TOKEN` and `LOKALISE_PROJECT_ID` secrets are correctly set
- Ensure the API token has read/write permissions

### Files Not Uploading to Lokalise
- Check the workflow logs in GitHub Actions
- Verify the file paths in the workflow match your repository structure
- Ensure the `base_lang` is set correctly (should be `en`)

### Pull Request Not Created
- Check that the workflow has write permissions to create PRs
- Ensure there are actual changes in Lokalise to pull
- Review workflow logs for any errors

## Additional Resources

- [Lokalise Documentation](https://docs.lokalise.com/)
- [Lokalise GitHub Actions Guide](https://lokalise.com/blog/github-actions-for-lokalise-translation/)
- [Lokalise Push Action](https://github.com/lokalise/lokalise-push-action)
- [Lokalise Pull Action](https://github.com/lokalise/lokalise-pull-action)

## Support

If you encounter issues, check:
1. GitHub Actions logs (Actions tab in your repository)
2. Lokalise activity log (in your Lokalise project)
3. This repository's Issues page for similar problems
