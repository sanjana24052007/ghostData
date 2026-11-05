def calculate_risk_score(result):

    # Identity not matched: score cannot be reliably assessed
    if not result["identity_found"]:
        return None

    exports = result["post_deletion_exports"]
    activities = result["activity_references"]

    # HIGH risk: data export available after deletion
    if exports > 0:
        return min(70 + (exports - 1) * 10, 100)

    # MEDIUM risk: related system activity found
    elif activities > 0:
        return min(40 + (activities - 1) * 5, 69)

    # LOW risk: no suspicious activity found
    else:
        return 10
