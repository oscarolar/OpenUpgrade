env = locals().get("env")

env.ref("payment.payment_provider_transfer").sequence = 7

env.cr.commit()
