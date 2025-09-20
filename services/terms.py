def to_term_code(season: str, year: int) -> str:
    """
    Convert season and year to Pitt term code.
    
    Args:
        season: "fall", "spring", or "summer"
        year: Full year (e.g., 2025)
    
    Returns:
        Term code string (e.g., "2251" for Fall 2025)
    """
    season_map = {
        "fall": "1",
        "spring": "4", 
        "summer": "7"
    }
    
    season_key = season.lower()
    if season_key not in season_map:
        raise ValueError(f"Invalid season: {season}. Must be 'fall', 'spring', or 'summer'")
    
    last_digit = season_map[season_key]
    year_code = year % 100  # Get last 2 digits of year
    
    # For spring terms, we need the previous year's code
    if season_key == "spring":
        year_code = (year - 1) % 100
    
    return f"2{year_code:02d}{last_digit}"
