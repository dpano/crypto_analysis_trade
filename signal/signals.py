def should_send_oportunity_signal(rsi_value, golden_cross_detected, death_cross_detected):
    if golden_cross_detected and not death_cross_detected and rsi_value < 70:
        return True
    elif rsi_value < 30:
        return True
    return False