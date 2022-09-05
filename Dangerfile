# If we merge into stable, ensure that the __init__.py and CHANGELOG files have been updated
if gitlab.branch_for_merge == 'stable'
  if !git.modified_files.include?("CHANGELOG.md")
    failure 'When merging to Stable, please update the version and add changes to the CHANGELOG', sticky: false
  end
end
