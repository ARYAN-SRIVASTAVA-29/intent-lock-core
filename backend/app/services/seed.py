from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Merchant, MerchantPolicy, Product

MERCHANT_ID = "merchant_demo_001"

DEMO_PRODUCTS = [
    {"sku":"SONY-XM5-BLK","product":"Sony WH-1000XM5","brand":"Sony","category":"ANC Headphones","price_minor":1_899_900,"inventory":17,"variant":"Black","delivery_days":2,"visible":True},
    {"sku":"SONY-XM5-BLU","product":"Sony WH-1000XM5","brand":"Sony","category":"ANC Headphones","price_minor":1_899_900,"inventory":8,"variant":"Blue","delivery_days":2,"visible":True},
    {"sku":"SONY-XM4-BLK","product":"Sony WH-1000XM4","brand":"Sony","category":"ANC Headphones","price_minor":1_699_900,"inventory":9,"variant":"Black","delivery_days":3,"visible":True},
    {"sku":"SONY-XM4-BLU","product":"Sony WH-1000XM4","brand":"Sony","category":"ANC Headphones","price_minor":1_699_900,"inventory":11,"variant":"Blue","delivery_days":3,"visible":True},
    {"sku":"SONY-WF1000-BLK","product":"Sony WF-1000XM5","brand":"Sony","category":"Earbuds","price_minor":2_199_000,"inventory":24,"variant":"Black","delivery_days":2,"visible":True},
    {"sku":"SONY-WF1000-SLV","product":"Sony WF-1000XM5","brand":"Sony","category":"Earbuds","price_minor":2_199_000,"inventory":12,"variant":"Silver","delivery_days":2,"visible":True},
    {"sku":"SONY-ULT-BLK","product":"Sony ULT Wear","brand":"Sony","category":"ANC Headphones","price_minor":1_499_900,"inventory":18,"variant":"Black","delivery_days":2,"visible":True},
    {"sku":"SONY-LINKS-BLK","product":"Sony LinkBuds S","brand":"Sony","category":"Earbuds","price_minor":1_299_900,"inventory":20,"variant":"Black","delivery_days":2,"visible":True},
    {"sku":"BOSE-QC-BLK","product":"Bose QuietComfort","brand":"Bose","category":"ANC Headphones","price_minor":2_399_900,"inventory":14,"variant":"Black","delivery_days":2,"visible":True},
    {"sku":"BOSE-QC-WHT","product":"Bose QuietComfort","brand":"Bose","category":"ANC Headphones","price_minor":2_399_900,"inventory":7,"variant":"White","delivery_days":2,"visible":True},
    {"sku":"BOSE-QCU-BLK","product":"Bose QuietComfort Ultra","brand":"Bose","category":"ANC Headphones","price_minor":3_499_900,"inventory":6,"variant":"Black","delivery_days":2,"visible":True},
    {"sku":"BOSE-OPEN-BLK","product":"Bose Ultra Open Earbuds","brand":"Bose","category":"Earbuds","price_minor":2_499_900,"inventory":10,"variant":"Black","delivery_days":3,"visible":True},
    {"sku":"BOSE-FLEX-BLK","product":"Bose SoundLink Flex","brand":"Bose","category":"Speakers","price_minor":1_299_900,"inventory":22,"variant":"Black","delivery_days":2,"visible":True},
    {"sku":"AIRPODS-MAX","product":"AirPods Max","brand":"Apple","category":"ANC Headphones","price_minor":3_299_900,"inventory":6,"variant":"Space Gray","delivery_days":3,"visible":True},
    {"sku":"AIRPODS-MAX-SLV","product":"AirPods Max","brand":"Apple","category":"ANC Headphones","price_minor":3_299_900,"inventory":4,"variant":"Silver","delivery_days":3,"visible":True},
    {"sku":"AIRPODS-PRO2","product":"AirPods Pro 2","brand":"Apple","category":"Earbuds","price_minor":2_499_900,"inventory":25,"variant":"White","delivery_days":2,"visible":True},
    {"sku":"HOMEPOD-MINI-MID","product":"HomePod Mini","brand":"Apple","category":"Speakers","price_minor":1_099_900,"inventory":13,"variant":"Midnight","delivery_days":3,"visible":True},
    {"sku":"JBL-LIVE-BLK","product":"JBL Live 770NC","brand":"JBL","category":"ANC Headphones","price_minor":999_900,"inventory":29,"variant":"Black","delivery_days":4,"visible":True},
    {"sku":"JBL-LIVE-BLU","product":"JBL Live 770NC","brand":"JBL","category":"ANC Headphones","price_minor":999_900,"inventory":31,"variant":"Blue","delivery_days":4,"visible":True},
    {"sku":"JBL-TOUR-BLK","product":"JBL Tour One M2","brand":"JBL","category":"ANC Headphones","price_minor":1_999_900,"inventory":8,"variant":"Black","delivery_days":3,"visible":True},
    {"sku":"JBL-CHARGE5-BLK","product":"JBL Charge 5","brand":"JBL","category":"Speakers","price_minor":1_499_900,"inventory":16,"variant":"Black","delivery_days":2,"visible":True},
    {"sku":"JBL-CHARGE5-BLU","product":"JBL Charge 5","brand":"JBL","category":"Speakers","price_minor":1_499_900,"inventory":10,"variant":"Blue","delivery_days":2,"visible":True},
    {"sku":"JBL-FLIP6-BLK","product":"JBL Flip 6","brand":"JBL","category":"Speakers","price_minor":999_900,"inventory":19,"variant":"Black","delivery_days":2,"visible":True},
    {"sku":"SENN-ACC-BLK","product":"Sennheiser Accentum","brand":"Sennheiser","category":"ANC Headphones","price_minor":1_249_900,"inventory":9,"variant":"Black","delivery_days":3,"visible":False},
    {"sku":"SENN-M4-BLK","product":"Sennheiser Momentum 4","brand":"Sennheiser","category":"ANC Headphones","price_minor":2_499_900,"inventory":7,"variant":"Black","delivery_days":3,"visible":True},
    {"sku":"SENN-MTW4-BLK","product":"Sennheiser Momentum True Wireless 4","brand":"Sennheiser","category":"Earbuds","price_minor":2_199_900,"inventory":11,"variant":"Black","delivery_days":3,"visible":True},
    {"sku":"MARSH-MON3-BLK","product":"Marshall Monitor III ANC","brand":"Marshall","category":"ANC Headphones","price_minor":2_999_900,"inventory":5,"variant":"Black","delivery_days":3,"visible":True},
    {"sku":"MARSH-MAJOR5-BLK","product":"Marshall Major V","brand":"Marshall","category":"ANC Headphones","price_minor":1_499_900,"inventory":15,"variant":"Black","delivery_days":3,"visible":True},
    {"sku":"MARSH-EMBER3-BLK","product":"Marshall Emberton III","brand":"Marshall","category":"Speakers","price_minor":1_799_900,"inventory":12,"variant":"Black","delivery_days":3,"visible":True},
    {"sku":"SONY-USBC-AUDIO","product":"Sony USB-C Audio Cable","brand":"Sony","category":"Accessories","price_minor":199_900,"inventory":42,"variant":"Black","delivery_days":2,"visible":True},
    {"sku":"BOSE-CASE-QC","product":"Bose Headphone Carry Case","brand":"Bose","category":"Accessories","price_minor":299_900,"inventory":18,"variant":"Black","delivery_days":2,"visible":True},
]



def seed_products_for_merchant(db: Session, merchant_id: str, replace: bool = False) -> None:
    if replace:
        db.query(Product).filter(Product.merchant_id == merchant_id).delete(synchronize_session=False)
        db.flush()
    existing_skus = set(db.scalars(select(Product.sku).where(Product.merchant_id == merchant_id)).all())
    for item in DEMO_PRODUCTS:
        if item["sku"] in existing_skus:
            continue
        db.add(Product(merchant_id=merchant_id, currency="INR", **item))


def seed_policy_for_merchant(db: Session, merchant_id: str) -> MerchantPolicy:
    policy = db.scalar(select(MerchantPolicy).where(MerchantPolicy.merchant_id == merchant_id, MerchantPolicy.version == "v1"))
    if policy is None:
        policy = MerchantPolicy(merchant_id=merchant_id, version="v1", status="PUBLISHED")
        db.add(policy)
    else:
        policy.status = "PUBLISHED"
    return policy


def seed_demo_data(db: Session) -> None:
    merchant = db.get(Merchant, MERCHANT_ID)
    if merchant is None:
        merchant = Merchant(
            id=MERCHANT_ID,
            name="Demo Audio Store",
            environment="Razorpay Test Mode",
            status="ACTIVE",
            onboarding_completed=True,
            payment_test_connected=True,
            discovery_enabled=True,
            identity_active=True,
            identity_algorithm="Ed25519",
            identity_fingerprint="demo_72f91a",
        )
        db.add(merchant)
        db.flush()
    seed_policy_for_merchant(db, MERCHANT_ID)
    seed_products_for_merchant(db, MERCHANT_ID)
    db.commit()
