env = locals().get("env")
forum = env["forum.forum"].search([], limit=1) or env["forum.forum"].create(
    {"name": "OpenUpgrade v20 test forum"}
)
post = env["forum.post"].create(
    {"name": "OpenUpgrade v20 test question", "forum_id": forum.id}
)
post.message_post(
    body="OpenUpgrade v20 test comment",
    message_type="comment",
    subtype_xmlid="mail.mt_comment",
)
follower = env["res.partner"].create({"name": "OpenUpgrade v20 forum follower"})
post.message_subscribe(partner_ids=follower.ids)
env.cr.commit()
